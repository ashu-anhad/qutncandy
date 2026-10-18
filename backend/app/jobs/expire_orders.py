"""Cancel unpaid orders past their payment window and return their stock.

Run from cron every few minutes:  */5 * * * *  cd backend && .venv/bin/python -m app.jobs.expire_orders
"""
from app.core.db import SessionLocal
from app.orders.service import expire_unpaid


def main() -> None:
    with SessionLocal() as db:
        count = expire_unpaid(db)
    print(f"Expired {count} unpaid order(s).")


if __name__ == "__main__":
    main()
