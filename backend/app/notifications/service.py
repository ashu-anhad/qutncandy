from typing import Protocol

from sqlalchemy.orm import Session

from app.auth.models import User
from app.core import messaging
from app.core.config import settings

from .models import Notification


class Tasks(Protocol):
    def add_task(self, func, *args, **kwargs) -> None: ...


class Outbox:
    """Collects sends for code that has no request (cron jobs); call flush() after committing."""

    def __init__(self):
        self.tasks = []

    def add_task(self, func, *args, **kwargs):
        self.tasks.append((func, args, kwargs))

    def flush(self):
        for func, args, kwargs in self.tasks:
            func(*args, **kwargs)
        self.tasks.clear()


def notify(db: Session, user_id: int, title: str, body: str, tasks: Tasks, link: str | None = None) -> None:
    """Save an in-app notification and queue the matching email.

    `tasks` is FastAPI's BackgroundTasks in a request (runs after the response, so after commit)
    or an Outbox in a job. Swap in a real queue here when email volume grows.
    """
    db.add(Notification(user_id=user_id, title=title, body=body, link=link))
    user = db.get(User, user_id)
    if user and user.email:
        text = f"Hi {user.name},\n\n{body}\n"
        if link:
            text += f"\n{settings.site_url}{link}\n"
        text += f"\n— {settings.store_name}"
        tasks.add_task(messaging.send_email, user.email, title, text)
