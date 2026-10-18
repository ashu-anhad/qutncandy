from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.admin.router import router as admin_router
from app.auth.router import router as auth_router
from app.cart.router import router as cart_router
from app.catalog.router import admin_router as catalog_admin_router
from app.catalog.router import router as catalog_router
from app.core.config import settings
from app.discounts.router import admin_router as discounts_admin_router
from app.notifications.router import router as notifications_router
from app.orders.router import admin_router as orders_admin_router
from app.orders.router import router as orders_router
from app.payments.router import router as payments_router
from app.reports.router import router as reports_router
from app.reviews.router import admin_router as reviews_admin_router
from app.reviews.router import router as reviews_router

app = FastAPI(title="QutnCandy API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(catalog_router)
app.include_router(catalog_admin_router)
app.include_router(cart_router)
app.include_router(orders_router)
app.include_router(payments_router)
app.include_router(orders_admin_router)
app.include_router(notifications_router)
app.include_router(reviews_router)
app.include_router(reviews_admin_router)
app.include_router(reports_router)
app.include_router(discounts_admin_router)

# Local media; in production serve this from S3/CDN instead (see core/storage.py).
Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
app.mount(settings.media_url, StaticFiles(directory=settings.media_dir), name="media")


@app.get("/api/health")
def health():
    return {"status": "ok"}
