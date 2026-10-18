import hashlib
import hmac
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.models import User
from app.catalog.models import Variant
from app.core.config import settings
from app.discounts import service as discount_service
from app.notifications.service import Tasks, notify
from app.orders.models import Order, OrderEvent

RAZORPAY_API = "https://api.razorpay.com/v1"


def enabled() -> bool:
    return bool(settings.razorpay_key_id and settings.razorpay_key_secret)


# ---------------- Razorpay API (the only network call; tests replace it)

def create_gateway_order(amount: int, receipt: str, notes: dict) -> str:
    """Create a Razorpay order for `amount` paise and return its id."""
    try:
        res = httpx.post(
            f"{RAZORPAY_API}/orders",
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
            json={"amount": amount, "currency": "INR", "receipt": receipt, "notes": notes},
            timeout=15,
        )
    except httpx.HTTPError:
        raise HTTPException(502, "Couldn't reach the payment provider. Please try again.")
    if res.status_code != 200:
        raise HTTPException(502, "The payment provider rejected the request. Please try again.")
    return res.json()["id"]


# ---------------- signatures

def _hmac(secret: str, message: bytes) -> str:
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def valid_payment_signature(razorpay_order_id: str, payment_id: str, signature: str) -> bool:
    expected = _hmac(settings.razorpay_key_secret, f"{razorpay_order_id}|{payment_id}".encode())
    return hmac.compare_digest(expected, signature)


def valid_webhook_signature(body: bytes, signature: str) -> bool:
    if not settings.razorpay_webhook_secret:
        return False
    return hmac.compare_digest(_hmac(settings.razorpay_webhook_secret, body), signature)


# ---------------- order <-> payment

def start_payment(db: Session, order: Order, user: User) -> dict:
    """Return popup options for an unpaid order, creating its Razorpay order on first use."""
    if not enabled():
        raise HTTPException(503, "Online payment isn't set up yet.")
    if order.status != "pending_payment":
        raise HTTPException(409, "This order doesn't need payment.")
    if order.expires_at and order.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(409, "The payment window for this order has closed. Please order again.")
    if not order.razorpay_order_id:
        order.razorpay_order_id = create_gateway_order(
            order.total, order.number, {"order_number": order.number, "user_id": str(user.id)}
        )
        db.commit()
    return {
        "key_id": settings.razorpay_key_id,
        "razorpay_order_id": order.razorpay_order_id,
        "amount": order.total,
        "currency": "INR",
        "name": settings.store_name,
        "description": f"Order {order.number}",
        "order_number": order.number,
        "prefill": {"name": user.name, "email": user.email or "", "contact": order.address.get("phone", "")},
    }


def _retake_stock(db: Session, order: Order) -> bool:
    """For a payment that lands after the hold expired: take the stock again, all or nothing."""
    for item in sorted(order.items, key=lambda i: i.variant_id or 0):
        taken = item.variant_id is not None and db.execute(
            update(Variant)
            .where(Variant.id == item.variant_id, Variant.stock >= item.qty)
            .values(stock=Variant.stock - item.qty)
            .execution_options(synchronize_session=False)
        ).rowcount
        if not taken:
            return False
    return True


def record_payment(
    db: Session, razorpay_order_id: str, payment_id: str, tasks: Tasks, amount: int | None = None
) -> Order | None:
    """Mark the order paid. Idempotent: safe for the browser callback and webhook to both call it."""
    order = db.scalar(select(Order).where(Order.razorpay_order_id == razorpay_order_id).with_for_update())
    if order is None:
        return None
    if order.razorpay_payment_id == payment_id and order.status != "pending_payment":
        return order  # already handled

    if amount is not None and amount != order.total:
        order.events.append(OrderEvent(status=order.status, note=f"Payment {payment_id} amount mismatch — check in Razorpay"))
        db.commit()
        return order

    link = f"/orders/{order.number}"
    if order.status == "pending_payment":
        order.status, order.expires_at = "paid", None
        order.razorpay_payment_id = payment_id
        order.events.append(OrderEvent(status="paid", note="Payment received"))
        notify(db, order.user_id, f"Order {order.number} confirmed",
               "We've received your payment and are preparing your order.", tasks, link)
    elif order.status == "cancelled" and not order.razorpay_payment_id:
        # Paid after the 15-minute hold ran out and the order was auto-cancelled.
        savepoint = db.begin_nested()
        if _retake_stock(db, order):
            savepoint.commit()
            if order.discount_code and (d := discount_service.find(db, order.discount_code)):
                discount_service.claim(db, d)  # honour the price they paid even if the code ran out
            order.status = "paid"
            order.razorpay_payment_id = payment_id
            order.events.append(OrderEvent(status="paid", note="Payment received after the hold expired"))
            notify(db, order.user_id, f"Order {order.number} confirmed",
                   "We've received your payment and are preparing your order.", tasks, link)
        else:
            savepoint.rollback()
            order.razorpay_payment_id = payment_id
            order.refund_status = "required"
            order.events.append(
                OrderEvent(status="cancelled", note="Payment received after items sold out — refund required")
            )
            notify(db, order.user_id, f"Refund coming for order {order.number}",
                   "Your payment arrived after the items sold out, so we'll refund it in full within 5–7 working days.",
                   tasks, link)
    db.commit()
    return order
