"""Sales reports straight from SQL aggregates. 'Sales' = orders that are paid, shipped or delivered."""
import csv
import io
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.orders.models import Order, OrderItem

IST = ZoneInfo("Asia/Kolkata")
SOLD = ("paid", "shipped", "delivered")


def date_range(start: date | None, end: date | None) -> tuple[date, date, datetime, datetime]:
    """Default to the last 30 days; returns the dates plus the matching [from, to) instants in IST."""
    end = end or datetime.now(IST).date()
    start = start or end - timedelta(days=29)
    if start > end:
        start, end = end, start
    return start, end, datetime.combine(start, time.min, IST), datetime.combine(end + timedelta(days=1), time.min, IST)


def sales(db: Session, start: date | None, end: date | None, group: str) -> dict:
    start, end, since, until = date_range(start, end)
    unit = "month" if group == "month" else "day"
    period = func.date_trunc(unit, func.timezone("Asia/Kolkata", Order.created_at)).label("period")
    rows = db.execute(
        select(
            period,
            func.count().label("orders"),
            func.sum(Order.total).label("revenue"),
            func.sum(Order.discount).label("discount"),
            func.sum(Order.shipping_fee).label("shipping"),
        )
        .where(Order.status.in_(SOLD), Order.created_at >= since, Order.created_at < until)
        .group_by(period)
        .order_by(period)
    ).all()
    by_period = {r.period.date(): r for r in rows}

    # Include empty days/months so charts show gaps honestly.
    periods, cursor = [], start.replace(day=1) if unit == "month" else start
    while cursor <= end:
        periods.append(cursor)
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1) if unit == "month" else cursor + timedelta(days=1)

    out = []
    for p in periods:
        r = by_period.get(p)
        orders, revenue = (r.orders, r.revenue) if r else (0, 0)
        out.append({
            "period": p.isoformat()[:7] if unit == "month" else p.isoformat(),
            "orders": orders,
            "revenue": revenue,
            "discount": r.discount if r else 0,
            "shipping": r.shipping if r else 0,
            "avg_order": revenue // orders if orders else 0,
        })
    total_orders = sum(r["orders"] for r in out)
    total_revenue = sum(r["revenue"] for r in out)
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "group": unit,
        "rows": out,
        "totals": {
            "orders": total_orders,
            "revenue": total_revenue,
            "discount": sum(r["discount"] for r in out),
            "avg_order": total_revenue // total_orders if total_orders else 0,
        },
    }


def top_products(db: Session, start: date | None, end: date | None, limit: int = 10) -> list[dict]:
    _, _, since, until = date_range(start, end)
    rows = db.execute(
        select(
            OrderItem.product_name,
            OrderItem.product_slug,
            func.sum(OrderItem.qty).label("units"),
            func.sum(OrderItem.line_total).label("sales"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.status.in_(SOLD), Order.created_at >= since, Order.created_at < until)
        .group_by(OrderItem.product_name, OrderItem.product_slug)
        .order_by(func.sum(OrderItem.line_total).desc())
        .limit(limit)
    ).all()
    # "sales" is the line total before order-level discounts.
    return [{"product": r.product_name, "slug": r.product_slug, "units": r.units, "sales": r.sales} for r in rows]


def discounts(db: Session, start: date | None, end: date | None) -> list[dict]:
    _, _, since, until = date_range(start, end)
    rows = db.execute(
        select(Order.discount_code, func.count().label("orders"), func.sum(Order.discount).label("discount"),
               func.sum(Order.total).label("revenue"))
        .where(Order.status.in_(SOLD), Order.discount_code.is_not(None),
               Order.created_at >= since, Order.created_at < until)
        .group_by(Order.discount_code)
        .order_by(func.count().desc())
    ).all()
    return [{"code": r.discount_code, "orders": r.orders, "discount": r.discount, "revenue": r.revenue} for r in rows]


def to_csv(rows: list[dict], money: tuple[str, ...]) -> str:
    """CSV with money columns converted from paise to rupees."""
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: f"{v / 100:.2f}" if k in money else v for k, v in row.items()})
    return buf.getvalue()
