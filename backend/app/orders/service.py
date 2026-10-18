import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.auth.models import Address, User
from app.cart import service as cart_service
from app.cart.schemas import CartLine
from app.catalog.models import Variant
from app.core.config import settings
from app.discounts import service as discount_service
from app.discounts.models import Discount
from app.notifications.service import Outbox, Tasks, notify

from .models import Order, OrderEvent, OrderItem


@dataclass
class Quote:
    lines: list[CartLine]
    subtotal: int = 0
    discount: int = 0
    discount_obj: Discount | None = None
    discount_error: str | None = None
    shipping_fee: int = 0
    problems: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.subtotal - self.discount + self.shipping_fee


def shipping_for(amount: int) -> int:
    return 0 if amount >= settings.free_shipping_min or amount == 0 else settings.shipping_fee


def build_quote(db: Session, user: User, discount_code: str | None) -> Quote:
    """The single place prices are worked out; used for the checkout preview and for placing orders."""
    lines = cart_service.user_lines(db, user.id)
    quote = Quote(lines=lines, subtotal=sum(line.line_total for line in lines))
    if not lines:
        quote.problems.append("Your cart is empty")
    for line in lines:
        if not line.available:
            what = f"{line.product_name} ({line.colour}, {line.size})"
            quote.problems.append(
                f"{what} is no longer available" if line.max_qty == 0 else f"Only {line.stock} of {what} left"
            )
    if discount_code and discount_code.strip():
        try:
            quote.discount_obj, quote.discount = discount_service.validate(db, discount_code, quote.subtotal)
        except discount_service.DiscountError as e:
            quote.discount_error = str(e)
    quote.shipping_fee = shipping_for(quote.subtotal - quote.discount)
    return quote


def quote_out(q: Quote) -> dict:
    return {
        "items": q.lines,
        "subtotal": q.subtotal,
        "discount": q.discount,
        "discount_code": q.discount_obj.code if q.discount_obj else None,
        "discount_error": q.discount_error,
        "shipping_fee": q.shipping_fee,
        "total": q.total,
        "can_place": not q.problems,
        "problems": q.problems,
    }


def _new_number() -> str:
    return f"QC{datetime.now(timezone.utc):%y%m%d}{secrets.token_hex(3).upper()}"


def _address_snapshot(a: Address) -> dict:
    return {k: getattr(a, k) for k in ("name", "phone", "line1", "line2", "city", "state", "pincode")}


def place_order(db: Session, user: User, address_id: int, discount_code: str | None) -> Order:
    address = db.get(Address, address_id)
    if address is None or address.user_id != user.id:
        raise HTTPException(404, "Address not found")

    quote = build_quote(db, user, discount_code)
    if quote.problems:
        raise HTTPException(409, quote.problems[0])
    if quote.discount_error:
        raise HTTPException(422, quote.discount_error)

    # Take stock atomically. "stock >= qty" in the UPDATE means two shoppers can never both get the
    # last piece, even across several API servers. Sorted ids keep lock order consistent.
    for line in sorted(quote.lines, key=lambda line: line.variant_id):
        taken = db.execute(
            update(Variant)
            .where(Variant.id == line.variant_id, Variant.is_active, Variant.stock >= line.qty)
            .values(stock=Variant.stock - line.qty)
            .execution_options(synchronize_session=False)
        ).rowcount
        if not taken:
            db.rollback()
            raise HTTPException(409, f"{line.product_name} ({line.colour}, {line.size}) just sold out")

    if quote.discount_obj and not discount_service.claim(db, quote.discount_obj):
        db.rollback()
        raise HTTPException(409, "This code has reached its usage limit")

    order = Order(
        number=_new_number(),
        user_id=user.id,
        status="pending_payment",
        subtotal=quote.subtotal,
        discount=quote.discount,
        discount_code=quote.discount_obj.code if quote.discount_obj else None,
        shipping_fee=quote.shipping_fee,
        total=quote.total,
        address=_address_snapshot(address),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.order_expiry_minutes),
        items=[
            OrderItem(
                variant_id=line.variant_id, product_id=line.product_id, product_name=line.product_name,
                product_slug=line.product_slug, size=line.size, colour=line.colour, sku=line.sku,
                image=line.image, unit_price=line.unit_price, qty=line.qty, line_total=line.line_total,
            )
            for line in quote.lines
        ],
        events=[OrderEvent(status="pending_payment", note="Order placed")],
    )
    db.add(order)
    cart_service.clear(db, user.id)
    db.commit()
    return get_order(db, order.number, user)


def get_order(db: Session, number: str, user: User | None = None, *, lock: bool = False) -> Order:
    stmt = select(Order).where(Order.number == number)
    if user is not None:
        stmt = stmt.where(Order.user_id == user.id)
    if lock:
        stmt = stmt.with_for_update()
    else:
        stmt = stmt.options(selectinload(Order.items), selectinload(Order.events))
    order = db.scalar(stmt)
    if order is None:
        raise HTTPException(404, "Order not found")
    return order


def _restore_stock(db: Session, order: Order) -> None:
    for item in order.items:
        if item.variant_id is not None:
            db.execute(
                update(Variant)
                .where(Variant.id == item.variant_id)
                .values(stock=Variant.stock + item.qty)
                .execution_options(synchronize_session=False)
            )


def cancel_order(db: Session, order: Order, note: str) -> None:
    """Cancel an order before it ships and give back its stock and discount use. Caller holds the row lock.

    A paid order is marked refund "required"; the refund itself is issued in the Razorpay dashboard.
    """
    if order.status not in ("pending_payment", "paid"):
        raise HTTPException(409, "This order can no longer be cancelled")
    _restore_stock(db, order)
    discount_service.release(db, order.discount_code)
    if order.status == "paid":
        order.refund_status = "required"
    order.status = "cancelled"
    order.expires_at = None
    order.events.append(OrderEvent(status="cancelled", note=note))


def expire_unpaid(db: Session, now: datetime | None = None) -> int:
    """Cancel every unpaid order past its expiry. Safe to run repeatedly and from several machines."""
    now = now or datetime.now(timezone.utc)
    outbox = Outbox()
    expired = db.scalars(
        select(Order)
        .where(Order.status == "pending_payment", Order.expires_at < now)
        .with_for_update(skip_locked=True)
    ).all()
    for order in expired:
        cancel_order(db, order, "Payment not received in time")
        notify(db, order.user_id, f"Order {order.number} cancelled",
               "We didn't receive payment in time, so your order was cancelled and the items released.",
               outbox, link=f"/orders/{order.number}")
    db.commit()
    outbox.flush()
    return len(expired)


# ---------------- fulfilment (admin)

def _link(order: Order) -> str:
    return f"/orders/{order.number}"


def ship(db: Session, order: Order, courier: str, tracking_no: str, note: str, tasks: Tasks) -> None:
    if order.status != "paid":
        raise HTTPException(409, "Only paid orders can be shipped")
    order.status, order.courier, order.tracking_no = "shipped", courier, tracking_no
    order.events.append(OrderEvent(status="shipped", note=note or f"{courier} · {tracking_no}"))
    notify(db, order.user_id, f"Order {order.number} has shipped",
           f"Your order is on its way with {courier}. Tracking number: {tracking_no}.", tasks, _link(order))


def deliver(db: Session, order: Order, note: str, tasks: Tasks) -> None:
    if order.status != "shipped":
        raise HTTPException(409, "Only shipped orders can be marked delivered")
    order.status = "delivered"
    order.events.append(OrderEvent(status="delivered", note=note))
    notify(db, order.user_id, f"Order {order.number} delivered",
           "Your order has been delivered. We hope you love it!", tasks, _link(order))


def store_cancel(db: Session, order: Order, note: str, tasks: Tasks) -> None:
    was_paid = order.status == "paid"
    cancel_order(db, order, note or "Cancelled by the store")
    body = "Your order has been cancelled by the store."
    if was_paid:
        body += " Your payment will be refunded to the original payment method within 5–7 working days."
    notify(db, order.user_id, f"Order {order.number} cancelled", body, tasks, _link(order))


def mark_refunded(db: Session, order: Order, note: str, tasks: Tasks) -> None:
    if order.refund_status != "required":
        raise HTTPException(409, "This order has no refund pending")
    order.refund_status = "refunded"
    order.events.append(OrderEvent(status=order.status, note=f"Refund issued{f' · {note}' if note else ''}"))
    notify(db, order.user_id, f"Refund issued for order {order.number}",
           "We've refunded your payment. It can take 5–7 working days to reach your account.", tasks, _link(order))


def summary(order: Order) -> dict:
    return {
        "number": order.number,
        "status": order.status,
        "created_at": order.created_at,
        "total": order.total,
        "item_count": sum(i.qty for i in order.items),
        "image": next((i.image for i in order.items if i.image), None),
    }
