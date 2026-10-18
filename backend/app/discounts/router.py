from fastapi import APIRouter, status
from sqlalchemy import select

from app.core.deps import AdminUser, DbSession
from app.core.errors import commit_or_409, get_or_404

from . import service
from .models import Discount
from .schemas import DiscountIn, DiscountOut, DiscountUpdate

admin_router = APIRouter(prefix="/api/admin/discounts", tags=["admin: discounts"])


@admin_router.get("", response_model=list[DiscountOut])
def list_discounts(_: AdminUser, db: DbSession):
    return db.scalars(select(Discount).order_by(Discount.created_at.desc())).all()


@admin_router.post("", response_model=DiscountOut, status_code=status.HTTP_201_CREATED)
def create_discount(payload: DiscountIn, _: AdminUser, db: DbSession):
    discount = Discount(**{**payload.model_dump(), "code": service.normalise(payload.code)})
    db.add(discount)
    commit_or_409(db, "A discount with that code already exists")
    db.refresh(discount)
    return discount


@admin_router.patch("/{discount_id}", response_model=DiscountOut)
def update_discount(discount_id: int, payload: DiscountUpdate, _: AdminUser, db: DbSession):
    discount = get_or_404(db, Discount, discount_id, "Discount")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(discount, k, v)
    db.commit()
    db.refresh(discount)
    return discount


@admin_router.delete("/{discount_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_discount(discount_id: int, _: AdminUser, db: DbSession):
    """Unused codes are deleted; codes already used on orders are deactivated instead."""
    discount = get_or_404(db, Discount, discount_id, "Discount")
    if discount.used_count:
        discount.is_active = False
    else:
        db.delete(discount)
    db.commit()
