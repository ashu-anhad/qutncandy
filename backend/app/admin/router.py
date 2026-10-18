from fastapi import APIRouter, Query
from sqlalchemy import func, select

from datetime import datetime, timedelta, timezone

from app.auth.models import User
from app.auth.schemas import UserOut
from app.catalog.models import Product, Variant
from app.core.config import settings
from app.core.deps import AdminUser, DbSession
from app.orders.models import Order

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
def list_users(
    _: AdminUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    total = db.scalar(select(func.count()).select_from(User))
    users = db.scalars(
        select(User).order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {"items": [UserOut.model_validate(u) for u in users], "total": total, "page": page}


@router.get("/stats")
def stats(_: AdminUser, db: DbSession):
    """Counts for the admin dashboard's work queues."""
    def count(*where):
        return db.scalar(select(func.count()).select_from(Order).where(*where))

    live = (Variant.is_active, Product.is_active)
    since = datetime.now(timezone.utc) - timedelta(days=1)
    return {
        "to_ship": count(Order.status == "paid"),
        "shipped": count(Order.status == "shipped"),
        "awaiting_payment": count(Order.status == "pending_payment"),
        "refunds_required": count(Order.refund_status == "required"),
        "low_stock": db.scalar(select(func.count()).select_from(Variant).join(Product).where(
            *live, Variant.stock > 0, Variant.stock <= settings.low_stock_threshold)),
        "out_of_stock": db.scalar(select(func.count()).select_from(Variant).join(Product).where(
            *live, Variant.stock == 0)),
        "revenue_24h": db.scalar(select(func.coalesce(func.sum(Order.total), 0)).where(
            Order.status.in_(("paid", "shipped", "delivered")), Order.created_at >= since)),
        "orders_24h": count(Order.status.in_(("paid", "shipped", "delivered")), Order.created_at >= since),
    }
