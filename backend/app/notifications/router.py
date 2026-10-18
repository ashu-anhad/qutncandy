from datetime import datetime, timezone

from fastapi import APIRouter, status
from sqlalchemy import func, select, update

from app.core.deps import CurrentUser, DbSession
from app.core.errors import get_or_404

from .models import Notification
from .schemas import NotificationList

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=NotificationList)
def list_notifications(user: CurrentUser, db: DbSession, limit: int = 30):
    items = db.scalars(
        select(Notification).where(Notification.user_id == user.id)
        .order_by(Notification.id.desc()).limit(min(limit, 100))
    ).all()
    unread = db.scalar(
        select(func.count()).where(Notification.user_id == user.id, Notification.read_at.is_(None))
    )
    return {"items": items, "unread": unread}


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_read(notification_id: int, user: CurrentUser, db: DbSession):
    n = get_or_404(db, Notification, notification_id, "Notification")
    if n.user_id == user.id and n.read_at is None:
        n.read_at = datetime.now(timezone.utc)
        db.commit()


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(user: CurrentUser, db: DbSession):
    db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(timezone.utc))
    )
    db.commit()
