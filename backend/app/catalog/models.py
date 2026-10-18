from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    sort_order: Mapped[int] = mapped_column(default=0, server_default="0")


class Product(TimestampMixin, Base):
    __tablename__ = "products"

    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), unique=True)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    fabric: Mapped[str] = mapped_column(String(100), default="Cotton", server_default="Cotton")
    base_price: Mapped[int]  # paise
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true", index=True)
    avg_rating: Mapped[float] = mapped_column(default=0, server_default="0")
    review_count: Mapped[int] = mapped_column(default=0, server_default="0")

    category: Mapped[Category] = relationship()
    variants: Mapped[list["Variant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="Variant.id"
    )
    images: Mapped[list["ProductImage"]] = relationship(
        cascade="all, delete-orphan", order_by="ProductImage.sort_order"
    )


class Variant(TimestampMixin, Base):
    __tablename__ = "variants"
    __table_args__ = (
        UniqueConstraint("product_id", "size", "colour"),
        CheckConstraint("stock >= 0", name="stock_non_negative"),
    )

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True)
    size: Mapped[str] = mapped_column(String(20))
    colour: Mapped[str] = mapped_column(String(40))
    price: Mapped[int | None]  # paise; overrides product.base_price when set
    stock: Mapped[int] = mapped_column(default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")

    product: Mapped[Product] = relationship(back_populates="variants")

    @property
    def effective_price(self) -> int:
        return self.price if self.price is not None else self.product.base_price


class ProductImage(TimestampMixin, Base):
    __tablename__ = "product_images"

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    colour: Mapped[str | None] = mapped_column(String(40))  # None = applies to every colour
    url: Mapped[str] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(default=0, server_default="0")
