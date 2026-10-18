from datetime import date

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.core.deps import AdminUser, DbSession

from . import service

router = APIRouter(prefix="/api/admin/reports", tags=["admin: reports"])

MONEY = ("revenue", "sales", "discount", "shipping", "avg_order")


def _csv(name: str, rows: list[dict], start: str, end: str) -> Response:
    return Response(
        service.to_csv(rows, MONEY),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{name}_{start}_to_{end}.csv"'},
    )


@router.get("/sales")
def sales(_: AdminUser, db: DbSession, start: date | None = None, end: date | None = None,
          group: str = Query("day", pattern="^(day|month)$"), format: str = "json"):
    data = service.sales(db, start, end, group)
    return _csv("sales", data["rows"], data["start"], data["end"]) if format == "csv" else data


@router.get("/top-products")
def top_products(_: AdminUser, db: DbSession, start: date | None = None, end: date | None = None,
                 limit: int = Query(10, ge=1, le=100), format: str = "json"):
    rows = service.top_products(db, start, end, limit)
    if format == "csv":
        s, e, *_ = service.date_range(start, end)
        return _csv("top_products", rows, s.isoformat(), e.isoformat())
    return rows


@router.get("/discounts")
def discounts(_: AdminUser, db: DbSession, start: date | None = None, end: date | None = None, format: str = "json"):
    rows = service.discounts(db, start, end)
    if format == "csv":
        s, e, *_ = service.date_range(start, end)
        return _csv("discounts", rows, s.isoformat(), e.isoformat())
    return rows
