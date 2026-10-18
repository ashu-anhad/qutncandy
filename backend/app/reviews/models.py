from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class Review(TimestampMixin, Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("product_id", "user_id"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),
    )

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    rating: Mapped[int]
    title: Mapped[str] = mapped_column(String(120), default="", server_default="")
    comment: Mapped[str] = mapped_column(String(2000), default="", server_default="")
    # pending -> approved | rejected. Only approved reviews are public and counted in ratings.
    status: Mapped[str] = mapped_column(String(10), default="pending", server_default="pending", index=True)
