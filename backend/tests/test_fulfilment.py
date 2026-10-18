import re
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import update

from app.catalog.models import Variant
from app.core import messaging
from app.core.db import SessionLocal
from app.orders import service as order_service
from app.orders.models import Order
from app.payments import service as payment_service
from app.notifications.service import Outbox

from .conftest import auth_header, make_admin, signup

ADDRESS = {"name": "Asha K", "phone": "9876543210", "line1": "12 Hazratganj", "city": "Lucknow",
           "state": "Uttar Pradesh", "pincode": "226001"}


@pytest.fixture
def emails(monkeypatch):
    sent = []
    monkeypatch.setattr(messaging, "send_email", lambda to, subject, body: sent.append((to, subject, body)))
    return sent


@pytest.fixture
def shop(client, emails):
    admin = make_admin(client)
    cat = client.post("/api/admin/categories", json={"name": "Kurtas"}, headers=admin).json()
    product = client.post("/api/admin/products", headers=admin, json={
        "name": "Noor Kurta", "category_id": cat["id"], "base_price": 250000,
        "variants": [{"size": "M", "colour": "White", "stock": 5}, {"size": "L", "colour": "White", "stock": 2},
                     {"size": "XL", "colour": "White", "stock": 0}],
    }).json()
    shopper = auth_header(signup(client, email="shopper@example.com")["access_token"])
    address_id = client.post("/api/me/addresses", json=ADDRESS, headers=shopper).json()["id"]
    variant_id = product["variants"][0]["id"]

    def place(paid=True, qty=1):
        client.post("/api/cart/items", json={"variant_id": variant_id, "qty": qty}, headers=shopper)
        number = client.post("/api/orders", json={"address_id": address_id}, headers=shopper).json()["number"]
        if paid:
            with SessionLocal() as db:
                db.execute(update(Order).where(Order.number == number).values(razorpay_order_id=f"rzp_{number}"))
                db.commit()
                payment_service.record_payment(db, f"rzp_{number}", f"pay_{number}", Outbox())
        return number

    return {"admin": admin, "shopper": shopper, "place": place, "variant_id": variant_id, "emails": emails}


def stock(variant_id):
    with SessionLocal() as db:
        return db.get(Variant, variant_id).stock


def act(client, shop, number, action, **body):
    return client.post(f"/api/admin/orders/{number}/{action}", json=body, headers=shop["admin"])


# ---------------- admin order list and detail

def test_admin_lists_and_filters_orders(client, shop):
    paid = shop["place"]()
    unpaid = shop["place"](paid=False)
    res = client.get("/api/admin/orders", headers=shop["admin"]).json()
    assert {o["number"] for o in res["items"]} == {paid, unpaid}
    assert [o["number"] for o in client.get("/api/admin/orders?status=paid", headers=shop["admin"]).json()["items"]] == [paid]
    found = client.get("/api/admin/orders?q=shopper@", headers=shop["admin"]).json()
    assert found["total"] == 2 and found["items"][0]["customer_email"] == "shopper@example.com"


def test_admin_order_detail_includes_customer_and_payment(client, shop):
    number = shop["place"]()
    d = client.get(f"/api/admin/orders/{number}", headers=shop["admin"]).json()
    assert d["customer"]["email"] == "shopper@example.com"
    assert d["razorpay_payment_id"] == f"pay_{number}"


def test_admin_orders_require_admin(client, shop):
    assert client.get("/api/admin/orders", headers=shop["shopper"]).status_code == 403


# ---------------- fulfilment flow

def test_ship_then_deliver_with_tracking_and_notifications(client, shop):
    number = shop["place"]()
    assert act(client, shop, number, "deliver").status_code == 409  # can't skip shipping
    res = act(client, shop, number, "ship", courier="Delhivery", tracking_no="DL123")
    assert res.status_code == 200 and res.json()["status"] == "shipped"
    assert act(client, shop, number, "ship", courier="X", tracking_no="Y").status_code == 409
    assert act(client, shop, number, "deliver").json()["status"] == "delivered"

    order = client.get(f"/api/orders/{number}", headers=shop["shopper"]).json()
    assert (order["courier"], order["tracking_no"]) == ("Delhivery", "DL123")
    assert [e["status"] for e in order["events"]] == ["pending_payment", "paid", "shipped", "delivered"]

    notes = client.get("/api/notifications", headers=shop["shopper"]).json()
    assert notes["unread"] == 3
    assert [n["title"] for n in notes["items"]] == [
        f"Order {number} delivered", f"Order {number} has shipped", f"Order {number} confirmed"]
    shipped_email = next(e for e in shop["emails"] if "shipped" in e[1])
    assert shipped_email[0] == "shopper@example.com" and "DL123" in shipped_email[2] and f"/orders/{number}" in shipped_email[2]


def test_unpaid_order_cannot_be_shipped(client, shop):
    number = shop["place"](paid=False)
    assert act(client, shop, number, "ship", courier="X", tracking_no="Y").status_code == 409


# ---------------- cancellations and refunds

def test_store_cancel_of_paid_order_restores_stock_and_flags_refund(client, shop):
    number = shop["place"](qty=2)
    assert stock(shop["variant_id"]) == 3
    res = act(client, shop, number, "cancel", note="Fabric defect")
    assert res.json()["status"] == "cancelled" and res.json()["refund_status"] == "required"
    assert stock(shop["variant_id"]) == 5
    queue = client.get("/api/admin/orders?refund=required", headers=shop["admin"]).json()
    assert [o["number"] for o in queue["items"]] == [number]
    assert "refunded" in shop["emails"][-1][2]

    res = act(client, shop, number, "refunded", note="rfnd_123")
    assert res.json()["refund_status"] == "refunded"
    assert "rfnd_123" in res.json()["events"][-1]["note"]
    assert act(client, shop, number, "refunded").status_code == 409
    assert client.get("/api/admin/orders?refund=required", headers=shop["admin"]).json()["total"] == 0


def test_shipped_order_cannot_be_cancelled(client, shop):
    number = shop["place"]()
    act(client, shop, number, "ship", courier="X", tracking_no="Y")
    assert act(client, shop, number, "cancel").status_code == 409


def test_customer_cannot_cancel_paid_order(client, shop):
    number = shop["place"]()
    assert client.post(f"/api/orders/{number}/cancel", headers=shop["shopper"]).status_code == 409


def test_expiry_notifies_customer(client, shop):
    number = shop["place"](paid=False)
    with SessionLocal() as db:
        db.execute(update(Order).where(Order.number == number)
                   .values(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)))
        db.commit()
        order_service.expire_unpaid(db)
    notes = client.get("/api/notifications", headers=shop["shopper"]).json()["items"]
    assert notes[0]["title"] == f"Order {number} cancelled"
    assert shop["emails"][-1][1] == f"Order {number} cancelled"


# ---------------- notifications

def test_mark_notifications_read(client, shop):
    shop["place"]()
    shop["place"]()
    notes = client.get("/api/notifications", headers=shop["shopper"]).json()
    assert notes["unread"] == 2
    client.post(f"/api/notifications/{notes['items'][0]['id']}/read", headers=shop["shopper"])
    assert client.get("/api/notifications", headers=shop["shopper"]).json()["unread"] == 1
    client.post("/api/notifications/read-all", headers=shop["shopper"])
    assert client.get("/api/notifications", headers=shop["shopper"]).json()["unread"] == 0


def test_notifications_are_private(client, shop):
    shop["place"]()
    other = auth_header(signup(client, email="other@example.com")["access_token"])
    assert client.get("/api/notifications", headers=other).json() == {"items": [], "unread": 0}


# ---------------- inventory and dashboard

def test_inventory_filters(client, shop):
    inv = lambda f: client.get(f"/api/admin/inventory?filter={f}", headers=shop["admin"]).json()  # noqa: E731
    assert inv("all")["total"] == 3
    assert [(v["size"], v["stock"]) for v in inv("low")["items"]] == [("L", 2)]
    assert [v["size"] for v in inv("out")["items"]] == ["XL"]
    assert inv("all")["items"][0]["stock"] == 0  # lowest stock first


def test_dashboard_stats(client, shop):
    shop["place"]()
    shop["place"](paid=False)
    s = client.get("/api/admin/stats", headers=shop["admin"]).json()
    assert (s["to_ship"], s["awaiting_payment"], s["refunds_required"]) == (1, 1, 0)
    assert (s["low_stock"], s["out_of_stock"]) == (2, 1)  # M is down to 3 (threshold), L has 2
    assert s["revenue_24h"] == 250000 and s["orders_24h"] == 1


# ---------------- password reset

def reset_token(emails):
    return re.search(r"token=([\w.-]+)", emails[-1][2]).group(1)


def test_forgot_and_reset_password(client, emails):
    old_token = signup(client, email="asha@example.com")["access_token"]
    assert client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"}).status_code == 204
    assert emails == []  # no email for unknown accounts, same response
    assert client.post("/api/auth/forgot-password", json={"email": "ASHA@example.com"}).status_code == 204
    token = reset_token(emails)

    res = client.post("/api/auth/reset-password", json={"token": token, "password": "brand-new-pass"})
    assert res.status_code == 200
    assert client.post("/api/auth/login", json={"email": "asha@example.com", "password": "brand-new-pass"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": "asha@example.com", "password": "secret123"}).status_code == 401
    assert client.get("/api/me", headers=auth_header(old_token)).status_code == 401  # other sessions signed out
    # link is single-use
    assert client.post("/api/auth/reset-password", json={"token": token, "password": "another-pass"}).status_code == 400


def test_reset_rejects_other_token_types(client, emails):
    access = signup(client, email="asha@example.com")["access_token"]
    assert client.post("/api/auth/reset-password", json={"token": access, "password": "brand-new-pass"}).status_code == 400
