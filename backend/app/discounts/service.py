from datetime import datetime, timezone

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from .models import Discount


class DiscountError(Exception):
    """Raised with a customer-facing message when a code can't be applied."""


def normalise(code: str) -> str:
    return code.strip().upper()


def find(db: Session, code: str) -> Discount | None:
    return db.scalar(select(Discount).where(Discount.code == normalise(code)))


def amount_for(discount: Discount, subtotal: int) -> int:
    if discount.type == "percent":
        amount = subtotal * discount.value // 100
        if discount.max_discount is not None:
            amount = min(amount, discount.max_discount)
    else:
        amount = discount.value
    return min(amount, subtotal)


def validate(db: Session, code: str, subtotal: int) -> tuple[Discount, int]:
    discount = find(db, code)
    now = datetime.now(timezone.utc)
    if discount is None or not discount.is_active:
        raise DiscountError("This code isn't valid")
    if discount.starts_at and now < discount.starts_at:
        raise DiscountError("This code isn't active yet")
    if discount.ends_at and now >= discount.ends_at:
        raise DiscountError("This code has expired")
    if discount.usage_limit is not None and discount.used_count >= discount.usage_limit:
        raise DiscountError("This code has reached its usage limit")
    if subtotal < discount.min_order:
        raise DiscountError(f"Add items worth ₹{(discount.min_order - subtotal) / 100:,.0f} more to use this code")
    return discount, amount_for(discount, subtotal)


def claim(db: Session, discount: Discount) -> bool:
    """Atomically take one use of the code; False if the limit was hit concurrently."""
    result = db.execute(
        update(Discount)
        .where(
            Discount.id == discount.id,
            or_(Discount.usage_limit.is_(None), Discount.used_count < Discount.usage_limit),
        )
        .values(used_count=Discount.used_count + 1)
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1


def release(db: Session, code: str | None) -> None:
    if not code:
        return
    db.execute(
        update(Discount)
        .where(Discount.code == code, Discount.used_count > 0)
        .values(used_count=func.greatest(Discount.used_count - 1, 0))
        .execution_options(synchronize_session=False)
    )
