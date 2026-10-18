from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class Discount(TimestampMixin, Base):
    __tablename__ = "discounts"

    code: Mapped[str] = mapped_column(String(40), unique=True)  # stored upper-case
    type: Mapped[str] = mapped_column(String(10))  # "percent" | "flat"
    value: Mapped[int]  # percent (1-100) or paise
    min_order: Mapped[int] = mapped_column(default=0, server_default="0")  # paise
    max_discount: Mapped[int | None]  # paise cap for percent codes
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    usage_limit: Mapped[int | None]
    # Claimed when an order is placed, released if that order is cancelled or expires.
    used_count: Mapped[int] = mapped_column(default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
