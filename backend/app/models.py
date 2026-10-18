"""Imports every model so Alembic and tests see the full schema. Add new feature models here."""
from app.auth.models import Address, OtpCode, User  # noqa: F401
from app.cart.models import CartItem  # noqa: F401
from app.catalog.models import Category, Product, ProductImage, Variant  # noqa: F401
from app.core.db import Base  # noqa: F401
from app.discounts.models import Discount  # noqa: F401
from app.notifications.models import Notification  # noqa: F401
from app.orders.models import Order, OrderEvent, OrderItem  # noqa: F401
from app.reviews.models import Review  # noqa: F401
