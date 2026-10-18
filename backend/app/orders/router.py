from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.auth.models import User
from app.core.deps import AdminUser, CurrentUser, DbSession

from . import service
from .models import Order
from .schemas import (
    AdminOrderOut,
    AdminOrderSummary,
    NoteIn,
    OrderOut,
    OrderSummary,
    PlaceOrderIn,
    QuoteIn,
    QuoteOut,
    ShipIn,
)

router = APIRouter(prefix="/api/orders", tags=["orders"])
admin_router = APIRouter(prefix="/api/admin/orders", tags=["admin: orders"])


@router.post("/quote", response_model=QuoteOut)
def quote(payload: QuoteIn, user: CurrentUser, db: DbSession):
    return service.quote_out(service.build_quote(db, user, payload.discount_code))


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def place_order(payload: PlaceOrderIn, user: CurrentUser, db: DbSession):
    return service.place_order(db, user, payload.address_id, payload.discount_code)


@router.get("")
def my_orders(user: CurrentUser, db: DbSession, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50)):
    base = select(Order).where(Order.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    orders = db.scalars(
        base.options(selectinload(Order.items))
        .order_by(Order.created_at.desc(), Order.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {"items": [OrderSummary(**service.summary(o)) for o in orders], "total": total, "page": page,
            "page_size": page_size}


@router.get("/{number}", response_model=OrderOut)
def get_order(number: str, user: CurrentUser, db: DbSession):
    return service.get_order(db, number, user)


@router.post("/{number}/cancel", response_model=OrderOut)
def cancel_order(number: str, user: CurrentUser, db: DbSession):
    order = service.get_order(db, number, user, lock=True)
    if order.status != "pending_payment":
        raise HTTPException(409, "Paid orders can't be cancelled online. Please contact us.")
    service.cancel_order(db, order, "Cancelled by customer")
    db.commit()
    return service.get_order(db, number, user)


# =========================== admin ===========================

def _admin_out(db, order: Order) -> dict:
    user = db.get(User, order.user_id)
    data = OrderOut.model_validate(order).model_dump()
    return {
        **data,
        "customer": {"id": user.id, "name": user.name, "email": user.email, "phone": user.phone},
        "razorpay_order_id": order.razorpay_order_id,
        "razorpay_payment_id": order.razorpay_payment_id,
    }


@admin_router.get("")
def admin_list_orders(
    _: AdminUser,
    db: DbSession,
    status: str | None = None,
    refund: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    base = select(Order, User).join(User, User.id == Order.user_id)
    if status:
        base = base.where(Order.status == status)
    if refund:
        base = base.where(Order.refund_status == refund)
    if q:
        like = f"%{q.strip()}%"
        base = base.where(or_(Order.number.ilike(like), User.email.ilike(like), User.name.ilike(like)))
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    # Oldest first for work queues (to ship, refunds); newest first otherwise.
    oldest_first = status == "paid" or refund == "required"
    order_by = (Order.created_at.asc(),) if oldest_first else (Order.created_at.desc(), Order.id.desc())
    rows = db.execute(
        base.options(selectinload(Order.items)).order_by(*order_by)
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    items = [
        AdminOrderSummary(**service.summary(o), customer_name=u.name, customer_email=u.email,
                          refund_status=o.refund_status)
        for o, u in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@admin_router.get("/{number}", response_model=AdminOrderOut)
def admin_get_order(number: str, _: AdminUser, db: DbSession):
    return _admin_out(db, service.get_order(db, number))


def _act(db, number: str, action, *args) -> dict:
    order = service.get_order(db, number, lock=True)
    action(db, order, *args)
    db.commit()
    return _admin_out(db, service.get_order(db, number))


@admin_router.post("/{number}/ship", response_model=AdminOrderOut)
def admin_ship(number: str, payload: ShipIn, _: AdminUser, db: DbSession, tasks: BackgroundTasks):
    return _act(db, number, service.ship, payload.courier, payload.tracking_no, payload.note, tasks)


@admin_router.post("/{number}/deliver", response_model=AdminOrderOut)
def admin_deliver(number: str, payload: NoteIn, _: AdminUser, db: DbSession, tasks: BackgroundTasks):
    return _act(db, number, service.deliver, payload.note, tasks)


@admin_router.post("/{number}/cancel", response_model=AdminOrderOut)
def admin_cancel(number: str, payload: NoteIn, _: AdminUser, db: DbSession, tasks: BackgroundTasks):
    return _act(db, number, service.store_cancel, payload.note, tasks)


@admin_router.post("/{number}/refunded", response_model=AdminOrderOut)
def admin_mark_refunded(number: str, payload: NoteIn, _: AdminUser, db: DbSession, tasks: BackgroundTasks):
    return _act(db, number, service.mark_refunded, payload.note, tasks)
