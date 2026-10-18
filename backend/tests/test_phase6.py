import re
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

from app.auth import service as auth_service
from app.auth.models import OtpCode, User
from app.core import messaging
from app.core.config import settings
from app.core.db import SessionLocal
from app.orders.models import Order
from app.payments import service as payment_service
from app.notifications.service import Outbox
from app.orders import service as order_service

from .conftest import auth_header, make_admin, signup

ADDRESS = {"name": "Asha K", "phone": "9876543210", "line1": "12 Hazratganj", "city": "Lucknow",
           "state": "Uttar Pradesh", "pincode": "226001"}


@pytest.fixture
def store(client):
    admin = make_admin(client)
    cat = client.post("/api/admin/categories", json={"name": "Kurtas"}, headers=admin).json()

    def product(name, price, stock=10):
        return client.post("/api/admin/products", headers=admin, json={
            "name": name, "category_id": cat["id"], "base_price": price,
            "variants": [{"size": "M", "colour": "White", "stock": stock}]}).json()

    return {"admin": admin, "product": product}


def buy(client, h, product, status="delivered", qty=1, code=None):
    """Place and pay for an order, then move it to `status`."""
    client.post("/api/cart/items", json={"variant_id": product["variants"][0]["id"], "qty": qty}, headers=h)
    addresses = client.get("/api/me/addresses", headers=h).json()
    address_id = addresses[0]["id"] if addresses else client.post("/api/me/addresses", json=ADDRESS, headers=h).json()["id"]
    number = client.post("/api/orders", json={"address_id": address_id, "discount_code": code}, headers=h).json()["number"]
    with SessionLocal() as db:
        db.execute(update(Order).where(Order.number == number).values(razorpay_order_id=f"rzp_{number}"))
        db.commit()
        payment_service.record_payment(db, f"rzp_{number}", f"pay_{number}", Outbox())
        order = order_service.get_order(db, number, lock=True)
        if status in ("shipped", "delivered"):
            order_service.ship(db, order, "Delhivery", "DL1", "", Outbox())
        if status == "delivered":
            order_service.deliver(db, order, "", Outbox())
        db.commit()
    return number


# ================= reviews

def test_only_delivered_buyers_can_review(client, store):
    kurta = store["product"]("Noor Kurta", 200000)
    h = auth_header(signup(client, email="asha@example.com", name="Asha Khan")["access_token"])
    review = {"rating": 5, "title": "Lovely", "comment": "Soft cotton, fine work"}
    assert client.get("/api/products/noor-kurta/reviews/mine", headers=h).json()["can_review"] is False
    assert client.put("/api/products/noor-kurta/reviews", json=review, headers=h).status_code == 403
    buy(client, h, kurta, status="shipped")
    assert client.put("/api/products/noor-kurta/reviews", json=review, headers=h).status_code == 403
    buy(client, h, kurta, status="delivered")
    res = client.put("/api/products/noor-kurta/reviews", json=review, headers=h)
    assert res.status_code == 200 and res.json()["review"]["status"] == "pending"


def test_approval_flow_updates_product_rating(client, store):
    kurta = store["product"]("Noor Kurta", 200000)
    ratings = {"a@example.com": 5, "b@example.com": 4, "c@example.com": 2}
    for email, stars in ratings.items():
        h = auth_header(signup(client, email=email, name="Asha Khan")["access_token"])
        buy(client, h, kurta)
        client.put("/api/products/noor-kurta/reviews", json={"rating": stars}, headers=h)

    public = client.get("/api/products/noor-kurta/reviews").json()
    assert public["total"] == 0 and public["items"] == []  # nothing public until approved

    pending = client.get("/api/admin/reviews?status=pending", headers=store["admin"]).json()["items"]
    assert len(pending) == 3 and pending[0]["customer_email"] == "a@example.com"
    by_rating = {r["rating"]: r["id"] for r in pending}
    client.post(f"/api/admin/reviews/{by_rating[5]}/approve", headers=store["admin"])
    client.post(f"/api/admin/reviews/{by_rating[4]}/approve", headers=store["admin"])
    client.post(f"/api/admin/reviews/{by_rating[2]}/reject", headers=store["admin"])

    public = client.get("/api/products/noor-kurta/reviews").json()
    assert (public["total"], public["avg_rating"]) == (2, 4.5)
    assert public["distribution"] == {"5": 1, "4": 1, "3": 0, "2": 0, "1": 0}  # JSON keys are strings
    assert public["items"][0]["author"] == "Asha K."
    product = client.get("/api/products/noor-kurta").json()
    assert (product["avg_rating"], product["review_count"]) == (4.5, 2)

    client.delete(f"/api/admin/reviews/{by_rating[5]}", headers=store["admin"])
    assert client.get("/api/products/noor-kurta").json()["avg_rating"] == 4.0


def test_editing_a_review_sends_it_back_to_moderation(client, store):
    kurta = store["product"]("Noor Kurta", 200000)
    h = auth_header(signup(client, email="asha@example.com")["access_token"])
    buy(client, h, kurta)
    review_id = client.put("/api/products/noor-kurta/reviews", json={"rating": 5}, headers=h).json()["review"]["id"]
    client.post(f"/api/admin/reviews/{review_id}/approve", headers=store["admin"])
    assert client.get("/api/products/noor-kurta").json()["review_count"] == 1
    mine = client.put("/api/products/noor-kurta/reviews", json={"rating": 1, "comment": "Changed my mind"}, headers=h).json()
    assert mine["review"]["status"] == "pending"
    assert client.get("/api/products/noor-kurta").json()["review_count"] == 0


def test_rating_validation_and_admin_only(client, store):
    store["product"]("Noor Kurta", 200000)
    h = auth_header(signup(client, email="asha@example.com")["access_token"])
    assert client.put("/api/products/noor-kurta/reviews", json={"rating": 6}, headers=h).status_code == 422
    assert client.get("/api/admin/reviews", headers=h).status_code == 403


# ================= reports

def test_sales_report_and_csv(client, store):
    kurta = store["product"]("Noor Kurta", 200000)
    dupatta = store["product"]("Mul Dupatta", 90000)
    client.post("/api/admin/discounts", json={"code": "TEN", "type": "percent", "value": 10}, headers=store["admin"])
    h = auth_header(signup(client, email="asha@example.com")["access_token"])
    buy(client, h, kurta, qty=2, code="TEN")  # 4000 - 400 = 3600, free shipping
    buy(client, h, dupatta)  # 900 + 99 shipping
    buy(client, h, dupatta, status="paid")
    cancelled = buy(client, h, kurta, status="paid")
    with SessionLocal() as db:
        order_service.store_cancel(db, order_service.get_order(db, cancelled, lock=True), "", Outbox())
        db.commit()

    s = client.get("/api/admin/reports/sales", headers=store["admin"]).json()
    assert len(s["rows"]) == 30  # empty days included
    assert s["totals"] == {"orders": 3, "revenue": 360000 + 99900 * 2, "discount": 40000,
                           "avg_order": (360000 + 99900 * 2) // 3}
    assert s["rows"][-1]["orders"] == 3  # all today (IST)

    monthly = client.get("/api/admin/reports/sales?group=month", headers=store["admin"]).json()
    assert monthly["rows"][-1]["orders"] == 3

    top = client.get("/api/admin/reports/top-products", headers=store["admin"]).json()
    assert [(t["product"], t["units"]) for t in top] == [("Noor Kurta", 2), ("Mul Dupatta", 2)]
    assert client.get("/api/admin/reports/discounts", headers=store["admin"]).json() == [
        {"code": "TEN", "orders": 1, "discount": 40000, "revenue": 360000}]

    csv_res = client.get("/api/admin/reports/top-products?format=csv", headers=store["admin"])
    assert csv_res.headers["content-type"].startswith("text/csv")
    # product sales are before the order-level discount (2 × ₹2,000)
    assert csv_res.text.splitlines()[:2] == ["product,slug,units,sales", "Noor Kurta,noor-kurta,2,4000.00"]


def test_reports_admin_only(client, store):
    h = auth_header(signup(client, email="asha@example.com")["access_token"])
    assert client.get("/api/admin/reports/sales", headers=h).status_code == 403


# ================= Google sign-in

@pytest.fixture
def google(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "client-123.apps.googleusercontent.com")
    tokens = {}

    def fake_verify(credential):
        return tokens.get(credential)

    monkeypatch.setattr(auth_service, "verify_google_token", fake_verify)
    return tokens


def test_providers_endpoint(client, google, monkeypatch):
    monkeypatch.setattr(settings, "otp_enabled", True)
    assert client.get("/api/auth/providers").json() == {
        "google_client_id": "client-123.apps.googleusercontent.com", "phone_otp": True}


def test_google_creates_then_reuses_account(client, google):
    google["tok"] = {"sub": "g-1", "email": "Meera@Gmail.com", "name": "Meera S", "email_verified": "true"}
    first = client.post("/api/auth/google", json={"credential": "tok" * 5})
    assert first.status_code == 401  # unknown token
    google["tok" * 5] = google.pop("tok")
    res = client.post("/api/auth/google", json={"credential": "tok" * 5})
    assert res.status_code == 200 and res.json()["user"]["email"] == "meera@gmail.com"
    again = client.post("/api/auth/google", json={"credential": "tok" * 5})
    assert again.json()["user"]["id"] == res.json()["user"]["id"]


def test_google_links_existing_email_account(client, google):
    existing = signup(client, email="meera@gmail.com", name="Meera")["user"]
    google["credential-x"] = {"sub": "g-2", "email": "meera@gmail.com", "name": "Meera S", "email_verified": "true"}
    res = client.post("/api/auth/google", json={"credential": "credential-x"})
    assert res.json()["user"]["id"] == existing["id"]
    with SessionLocal() as db:
        assert db.get(User, existing["id"]).google_id == "g-2"
    # password login still works for the linked account
    assert client.post("/api/auth/login", json={"email": "meera@gmail.com", "password": "secret123"}).status_code == 200


def test_google_disabled_without_client_id(client, monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "")
    assert client.post("/api/auth/google", json={"credential": "anything-long"}).status_code == 503


# ================= phone OTP

@pytest.fixture
def sms(monkeypatch):
    monkeypatch.setattr(settings, "otp_enabled", True)
    sent = []
    monkeypatch.setattr(messaging, "send_sms", lambda phone, text: sent.append((phone, text)))
    return sent


def last_code(sms):
    return re.match(r"(\d{6})", sms[-1][1]).group(1)


def test_otp_signup_then_login(client, sms):
    assert client.post("/api/auth/otp/send", json={"phone": "+91 98765 43210"}).status_code == 204
    assert sms[-1][0] == "9876543210"
    code = last_code(sms)
    res = client.post("/api/auth/otp/verify", json={"phone": "9876543210", "code": code})
    assert res.status_code == 428  # new number: name needed, code kept
    res = client.post("/api/auth/otp/verify", json={"phone": "09876543210", "code": code, "name": "Ravi"})
    assert res.status_code == 200 and res.json()["user"]["phone"] == "9876543210"
    assert client.post("/api/auth/otp/verify", json={"phone": "9876543210", "code": code}).status_code == 400  # used

    with SessionLocal() as db:  # skip the 30 s resend wait
        db.execute(update(OtpCode).values(created_at=datetime.now(timezone.utc) - timedelta(minutes=1)))
        db.commit()
    client.post("/api/auth/otp/send", json={"phone": "9876543210"})
    again = client.post("/api/auth/otp/verify", json={"phone": "9876543210", "code": last_code(sms)})
    assert again.json()["user"]["id"] == res.json()["user"]["id"]


def test_otp_wrong_code_attempt_limit(client, sms):
    client.post("/api/auth/otp/send", json={"phone": "9876543210"})
    code = last_code(sms)
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        assert client.post("/api/auth/otp/verify", json={"phone": "9876543210", "code": wrong, "name": "R"}).status_code == 400
    res = client.post("/api/auth/otp/verify", json={"phone": "9876543210", "code": code, "name": "R"})
    assert res.status_code == 400 and "Too many" in res.json()["detail"]


def test_otp_expiry_rate_limit_and_validation(client, sms):
    assert client.post("/api/auth/otp/send", json={"phone": "12345"}).status_code == 422
    assert client.post("/api/auth/otp/send", json={"phone": "5876543210"}).status_code == 422
    client.post("/api/auth/otp/send", json={"phone": "9876543210"})
    assert client.post("/api/auth/otp/send", json={"phone": "9876543210"}).status_code == 429  # 30 s wait
    with SessionLocal() as db:
        db.execute(update(OtpCode).values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        db.commit()
    res = client.post("/api/auth/otp/verify", json={"phone": "9876543210", "code": last_code(sms), "name": "R"})
    assert res.status_code == 400 and "expired" in res.json()["detail"]


def test_otp_hourly_limit(client, sms):
    for i in range(5):
        with SessionLocal() as db:
            db.execute(update(OtpCode).values(created_at=OtpCode.created_at - timedelta(minutes=1)))
            db.commit()
        assert client.post("/api/auth/otp/send", json={"phone": "9876543210"}).status_code == 204
    with SessionLocal() as db:
        db.execute(update(OtpCode).values(created_at=OtpCode.created_at - timedelta(minutes=1)))
        db.commit()
        assert len(db.scalars(select(OtpCode)).all()) == 5
    assert client.post("/api/auth/otp/send", json={"phone": "9876543210"}).status_code == 429


def test_otp_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "otp_enabled", False)
    assert client.post("/api/auth/otp/send", json={"phone": "9876543210"}).status_code == 503
