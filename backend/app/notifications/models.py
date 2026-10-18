from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(String(1000), default="", server_default="")
    link: Mapped[str | None] = mapped_column(String(300))  # path inside the storefront, e.g. /orders/CNC…
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
