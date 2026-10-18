from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin

# pending_payment -> paid -> shipped -> delivered; pending_payment/paid -> cancelled
STATUSES = ("pending_payment", "paid", "shipped", "delivered", "cancelled")
# Set when money was taken but the order can't be fulfilled: "required" -> "refunded".
REFUND_STATUSES = ("required", "refunded")


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    number: Mapped[str] = mapped_column(String(20), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    subtotal: Mapped[int]  # all money in paise
    discount: Mapped[int] = mapped_column(default=0, server_default="0")
    shipping_fee: Mapped[int] = mapped_column(default=0, server_default="0")
    total: Mapped[int]
    discount_code: Mapped[str | None] = mapped_column(String(40))
    address: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"))  # copy at order time
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    razorpay_order_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(64))
    courier: Mapped[str | None] = mapped_column(String(100))
    tracking_no: Mapped[str | None] = mapped_column(String(100))
    refund_status: Mapped[str | None] = mapped_column(String(20), index=True)

    items: Mapped[list["OrderItem"]] = relationship(cascade="all, delete-orphan", order_by="OrderItem.id")
    events: Mapped[list["OrderEvent"]] = relationship(cascade="all, delete-orphan", order_by="OrderEvent.id")


class OrderItem(TimestampMixin, Base):
    """A snapshot of what was bought, so later catalog edits or deletions never change past orders."""

    __tablename__ = "order_items"

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("variants.id", ondelete="SET NULL"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), index=True)
    product_name: Mapped[str] = mapped_column(String(200))
    product_slug: Mapped[str] = mapped_column(String(220))
    size: Mapped[str] = mapped_column(String(20))
    colour: Mapped[str] = mapped_column(String(40))
    sku: Mapped[str] = mapped_column(String(64))
    image: Mapped[str | None] = mapped_column(String(500))
    unit_price: Mapped[int]
    qty: Mapped[int]
    line_total: Mapped[int]


class OrderEvent(TimestampMixin, Base):
    """One row per status change; drives the tracking timeline."""

    __tablename__ = "order_events"

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(String(500), default="", server_default="")
