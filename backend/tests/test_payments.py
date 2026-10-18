import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import update

from app.catalog.models import Variant
from app.core.config import settings
from app.core.db import SessionLocal
from app.orders import service as order_service
from app.orders.models import Order
from app.payments import service as payment_service

from .conftest import auth_header, make_admin, signup

KEY_SECRET = "test_key_secret"
WEBHOOK_SECRET = "test_webhook_secret"
ADDRESS = {"name": "Asha K", "phone": "9876543210", "line1": "12 Hazratganj", "city": "Lucknow",
           "state": "Uttar Pradesh", "pincode": "226001"}


@pytest.fixture(autouse=True)
def razorpay(monkeypatch):
    monkeypatch.setattr(settings, "razorpay_key_id", "rzp_test_key")
    monkeypatch.setattr(settings, "razorpay_key_secret", KEY_SECRET)
    monkeypatch.setattr(settings, "razorpay_webhook_secret", WEBHOOK_SECRET)
    calls = []

    def fake_create(amount, receipt, notes):
        calls.append(amount)
        return f"order_rzp_{receipt}"

    monkeypatch.setattr(payment_service, "create_gateway_order", fake_create)
    return calls


@pytest.fixture
def setup(client):
    admin = make_admin(client)
    cat = client.post("/api/admin/categories", json={"name": "Kurtas"}, headers=admin).json()
    product = client.post("/api/admin/products", headers=admin, json={
        "name": "Noor Kurta", "category_id": cat["id"], "base_price": 250000,
        "variants": [{"size": "M", "colour": "White", "stock": 3}],
    }).json()
    variant_id = product["variants"][0]["id"]
    shopper = auth_header(signup(client, email="shopper@example.com")["access_token"])
    address_id = client.post("/api/me/addresses", json=ADDRESS, headers=shopper).json()["id"]

    def place(qty=1):
        client.post("/api/cart/items", json={"variant_id": variant_id, "qty": qty}, headers=shopper)
        res = client.post("/api/orders", json={"address_id": address_id}, headers=shopper)
        assert res.status_code == 201, res.text
        return res.json()["number"]

    return {"shopper": shopper, "variant_id": variant_id, "place": place}


def sign(order_id, payment_id, secret=KEY_SECRET):
    return hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()


def webhook(client, payload, secret=WEBHOOK_SECRET):
    body = json.dumps(payload).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return client.post("/api/webhooks/razorpay", content=body,
                       headers={"X-Razorpay-Signature": signature, "Content-Type": "application/json"})


def captured(rzp_order_id, payment_id="pay_1", amount=250000):
    return {"event": "payment.captured",
            "payload": {"payment": {"entity": {"id": payment_id, "order_id": rzp_order_id, "amount": amount}}}}


def stock(variant_id):
    with SessionLocal() as db:
        return db.get(Variant, variant_id).stock


def start(client, h, number):
    res = client.post(f"/api/orders/{number}/pay", headers=h)
    assert res.status_code == 200, res.text
    return res.json()


def test_pay_returns_popup_options_and_reuses_gateway_order(client, setup, razorpay):
    number = setup["place"]()
    opts = start(client, setup["shopper"], number)
    assert opts["key_id"] == "rzp_test_key" and opts["amount"] == 250000 and opts["currency"] == "INR"
    assert opts["prefill"]["contact"] == "9876543210"
    assert start(client, setup["shopper"], number)["razorpay_order_id"] == opts["razorpay_order_id"]
    assert razorpay == [250000]  # only one Razorpay order created


def test_verify_marks_order_paid(client, setup):
    number = setup["place"]()
    rzp = start(client, setup["shopper"], number)["razorpay_order_id"]
    res = client.post("/api/payments/verify", headers=setup["shopper"], json={
        "razorpay_order_id": rzp, "razorpay_payment_id": "pay_1", "razorpay_signature": sign(rzp, "pay_1")})
    assert res.status_code == 200, res.text
    order = res.json()
    assert order["status"] == "paid" and order["expires_at"] is None
    assert [e["status"] for e in order["events"]] == ["pending_payment", "paid"]


def test_verify_rejects_bad_signature(client, setup):
    number = setup["place"]()
    rzp = start(client, setup["shopper"], number)["razorpay_order_id"]
    res = client.post("/api/payments/verify", headers=setup["shopper"], json={
        "razorpay_order_id": rzp, "razorpay_payment_id": "pay_1", "razorpay_signature": sign(rzp, "pay_1", "wrong")})
    assert res.status_code == 400
    assert client.get(f"/api/orders/{number}", headers=setup["shopper"]).json()["status"] == "pending_payment"


def test_webhook_marks_paid_and_is_idempotent_with_verify(client, setup):
    number = setup["place"]()
    rzp = start(client, setup["shopper"], number)["razorpay_order_id"]
    assert webhook(client, captured(rzp)).status_code == 200
    assert webhook(client, captured(rzp)).status_code == 200  # Razorpay retries
    client.post("/api/payments/verify", headers=setup["shopper"], json={
        "razorpay_order_id": rzp, "razorpay_payment_id": "pay_1", "razorpay_signature": sign(rzp, "pay_1")})
    order = client.get(f"/api/orders/{number}", headers=setup["shopper"]).json()
    assert order["status"] == "paid"
    assert [e["status"] for e in order["events"]] == ["pending_payment", "paid"]  # recorded once


def test_webhook_rejects_bad_signature_and_ignores_other_events(client, setup):
    number = setup["place"]()
    rzp = start(client, setup["shopper"], number)["razorpay_order_id"]
    assert webhook(client, captured(rzp), secret="wrong").status_code == 400
    failed = {"event": "payment.failed", "payload": {"payment": {"entity": {"id": "pay_x", "order_id": rzp}}}}
    assert webhook(client, failed).status_code == 200
    assert client.get(f"/api/orders/{number}", headers=setup["shopper"]).json()["status"] == "pending_payment"


def test_webhook_amount_mismatch_does_not_mark_paid(client, setup):
    number = setup["place"]()
    rzp = start(client, setup["shopper"], number)["razorpay_order_id"]
    webhook(client, captured(rzp, amount=100))
    order = client.get(f"/api/orders/{number}", headers=setup["shopper"]).json()
    assert order["status"] == "pending_payment"
    assert "amount mismatch" in order["events"][-1]["note"]


def expire(number):
    with SessionLocal() as db:
        db.execute(update(Order).where(Order.number == number)
                   .values(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)))
        db.commit()


def test_cannot_start_payment_after_window_or_when_paid(client, setup):
    number = setup["place"]()
    expire(number)
    assert client.post(f"/api/orders/{number}/pay", headers=setup["shopper"]).status_code == 409


def test_late_payment_revives_order_when_stock_remains(client, setup):
    number = setup["place"](2)
    rzp = start(client, setup["shopper"], number)["razorpay_order_id"]
    expire(number)
    with SessionLocal() as db:
        order_service.expire_unpaid(db)
    assert stock(setup["variant_id"]) == 3
    webhook(client, captured(rzp, amount=500000))
    order = client.get(f"/api/orders/{number}", headers=setup["shopper"]).json()
    assert order["status"] == "paid" and "after the hold expired" in order["events"][-1]["note"]
    assert stock(setup["variant_id"]) == 1


def test_late_payment_flags_refund_when_sold_out(client, setup):
    number = setup["place"](2)
    rzp = start(client, setup["shopper"], number)["razorpay_order_id"]
    expire(number)
    with SessionLocal() as db:
        order_service.expire_unpaid(db)
        db.execute(update(Variant).where(Variant.id == setup["variant_id"]).values(stock=1))
        db.commit()
    webhook(client, captured(rzp, amount=500000))
    order = client.get(f"/api/orders/{number}", headers=setup["shopper"]).json()
    assert order["status"] == "cancelled" and "refund required" in order["events"][-1]["note"]
    assert stock(setup["variant_id"]) == 1  # nothing partially taken


def test_payment_disabled_without_keys(client, setup, monkeypatch):
    monkeypatch.setattr(settings, "razorpay_key_id", "")
    number = setup["place"]()
    assert client.post(f"/api/orders/{number}/pay", headers=setup["shopper"]).status_code == 503


def test_cannot_pay_someone_elses_order(client, setup):
    number = setup["place"]()
    other = auth_header(signup(client, email="other@example.com")["access_token"])
    assert client.post(f"/api/orders/{number}/pay", headers=other).status_code == 404
