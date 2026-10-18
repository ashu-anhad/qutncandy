import threading
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import select, update

from app.auth.models import Address, User
from app.catalog.models import Variant
from app.core.db import SessionLocal
from app.discounts.models import Discount
from app.orders import service as order_service
from app.orders.models import Order

from .conftest import auth_header, make_admin, signup

ADDRESS = {"name": "Asha K", "phone": "9876543210", "line1": "12 Hazratganj", "city": "Lucknow",
           "state": "Uttar Pradesh", "pincode": "226001"}


@pytest.fixture
def admin(client):
    return make_admin(client)


@pytest.fixture
def shop(client, admin):
    """One kurta (₹1,500; XXL ₹1,700) and one dupatta (₹900) with known stock."""
    cat = client.post("/api/admin/categories", json={"name": "Kurtas"}, headers=admin).json()
    kurta = client.post("/api/admin/products", headers=admin, json={
        "name": "Noor Kurta", "category_id": cat["id"], "base_price": 150000,
        "variants": [{"size": "M", "colour": "White", "stock": 5},
                     {"size": "XXL", "colour": "White", "stock": 1, "price": 170000}],
    }).json()
    dupatta = client.post("/api/admin/products", headers=admin, json={
        "name": "Mul Dupatta", "category_id": cat["id"], "base_price": 90000,
        "variants": [{"size": "Free Size", "colour": "Pink", "stock": 2}],
    }).json()
    return {"m": kurta["variants"][0]["id"], "xxl": kurta["variants"][1]["id"], "dupatta": dupatta["variants"][0]["id"]}


@pytest.fixture
def shopper(client):
    return auth_header(signup(client, email="shopper@example.com")["access_token"])


def add(client, h, variant_id, qty=1):
    res = client.post("/api/cart/items", json={"variant_id": variant_id, "qty": qty}, headers=h)
    assert res.status_code == 200, res.text
    return res.json()


def stock(variant_id):
    with SessionLocal() as db:
        return db.get(Variant, variant_id).stock


def new_address(client, h, **extra):
    res = client.post("/api/me/addresses", json={**ADDRESS, **extra}, headers=h)
    assert res.status_code == 201, res.text
    return res.json()


# ---------------- cart

def test_cart_add_caps_at_stock_and_sums(client, shop, shopper):
    add(client, shopper, shop["m"], 2)
    cart = add(client, shopper, shop["m"], 10)  # only 5 in stock
    assert cart["items"][0]["qty"] == 5
    cart = add(client, shopper, shop["dupatta"])
    assert cart["item_count"] == 6 and cart["subtotal"] == 5 * 150000 + 90000


def test_cart_update_and_remove(client, shop, shopper):
    add(client, shopper, shop["m"], 2)
    cart = client.patch(f"/api/cart/items/{shop['m']}", json={"qty": 1}, headers=shopper).json()
    assert cart["items"][0]["qty"] == 1
    assert client.delete(f"/api/cart/items/{shop['m']}", headers=shopper).json()["items"] == []


def test_out_of_stock_cannot_be_added(client, admin, shop, shopper):
    client.patch(f"/api/admin/variants/{shop['dupatta']}", json={"stock": 0}, headers=admin)
    res = client.post("/api/cart/items", json={"variant_id": shop["dupatta"]}, headers=shopper)
    assert res.status_code == 409


def test_guest_preview_and_merge(client, shop, shopper):
    guest = {"items": [{"variant_id": shop["xxl"], "qty": 1}, {"variant_id": 99999, "qty": 1}]}
    preview = client.post("/api/cart/preview", json=guest).json()
    assert [i["unit_price"] for i in preview["items"]] == [170000]  # unknown variant dropped
    add(client, shopper, shop["m"])
    merged = client.post("/api/cart/merge", json=guest, headers=shopper).json()
    assert {i["variant_id"] for i in merged["items"]} == {shop["m"], shop["xxl"]}


# ---------------- addresses

def test_first_address_becomes_default_and_default_moves(client, shopper):
    a = new_address(client, shopper)
    assert a["is_default"]
    b = new_address(client, shopper, is_default=True, line1="5 Aminabad")
    listed = client.get("/api/me/addresses", headers=shopper).json()
    assert [x["id"] for x in listed if x["is_default"]] == [b["id"]]
    client.delete(f"/api/me/addresses/{b['id']}", headers=shopper)
    assert client.get("/api/me/addresses", headers=shopper).json()[0]["is_default"]


def test_address_validation_and_ownership(client, shopper):
    assert client.post("/api/me/addresses", json={**ADDRESS, "pincode": "12345"}, headers=shopper).status_code == 422
    assert client.post("/api/me/addresses", json={**ADDRESS, "phone": "12345"}, headers=shopper).status_code == 422
    a = new_address(client, shopper)
    other = auth_header(signup(client, email="other@example.com")["access_token"])
    assert client.delete(f"/api/me/addresses/{a['id']}", headers=other).status_code == 404


# ---------------- discounts and quote

def make_discount(client, admin, **data):
    res = client.post("/api/admin/discounts", json={"type": "percent", "value": 10, **data}, headers=admin)
    assert res.status_code == 201, res.text
    return res.json()


def quote(client, h, code=None):
    return client.post("/api/orders/quote", json={"discount_code": code}, headers=h).json()


def test_quote_shipping_rules(client, shop, shopper):
    add(client, shopper, shop["dupatta"])  # ₹900 -> pays shipping
    q = quote(client, shopper)
    assert (q["subtotal"], q["shipping_fee"], q["total"]) == (90000, 9900, 99900)
    add(client, shopper, shop["xxl"])  # ₹2,600 -> free shipping
    assert quote(client, shopper)["shipping_fee"] == 0


def test_percent_discount_with_cap(client, admin, shop, shopper):
    make_discount(client, admin, code="eid20", value=20, max_discount=30000)
    add(client, shopper, shop["m"], 2)  # ₹3,000 -> 20% = ₹600, capped at ₹300
    q = quote(client, shopper, " Eid20 ")
    assert (q["discount"], q["discount_code"], q["total"]) == (30000, "EID20", 270000)


def test_flat_discount_rules(client, admin, shop, shopper):
    make_discount(client, admin, code="FLAT200", type="flat", value=20000, min_order=200000)
    make_discount(client, admin, code="OLD", ends_at=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat())
    add(client, shopper, shop["m"])
    assert "more to use this code" in quote(client, shopper, "FLAT200")["discount_error"]
    assert quote(client, shopper, "OLD")["discount_error"] == "This code has expired"
    assert quote(client, shopper, "NOPE")["discount_error"] == "This code isn't valid"
    add(client, shopper, shop["m"])
    assert quote(client, shopper, "FLAT200")["discount"] == 20000


def test_discount_validation_on_create(client, admin):
    res = client.post("/api/admin/discounts", json={"code": "BAD", "type": "percent", "value": 150}, headers=admin)
    assert res.status_code == 422


# ---------------- placing orders

def test_place_order_takes_stock_and_clears_cart(client, admin, shop, shopper):
    make_discount(client, admin, code="WELCOME10")
    add(client, shopper, shop["m"], 2)
    add(client, shopper, shop["dupatta"])
    address = new_address(client, shopper)
    res = client.post("/api/orders", json={"address_id": address["id"], "discount_code": "welcome10"}, headers=shopper)
    assert res.status_code == 201, res.text
    order = res.json()
    assert order["status"] == "pending_payment" and order["number"].startswith("QC")
    assert (order["subtotal"], order["discount"], order["shipping_fee"]) == (390000, 39000, 0)
    assert order["total"] == 351000
    assert order["address"]["city"] == "Lucknow"
    assert [e["status"] for e in order["events"]] == ["pending_payment"]
    assert (stock(shop["m"]), stock(shop["dupatta"])) == (3, 1)
    assert client.get("/api/cart", headers=shopper).json()["items"] == []
    assert client.get("/api/admin/discounts", headers=admin).json()[0]["used_count"] == 1
    assert client.get("/api/orders", headers=shopper).json()["items"][0]["item_count"] == 3


def test_cannot_place_with_empty_cart_or_bad_code(client, shop, shopper):
    address = new_address(client, shopper)
    assert client.post("/api/orders", json={"address_id": address["id"]}, headers=shopper).status_code == 409
    add(client, shopper, shop["m"])
    res = client.post("/api/orders", json={"address_id": address["id"], "discount_code": "NOPE"}, headers=shopper)
    assert res.status_code == 422


def test_stock_change_after_adding_blocks_order(client, admin, shop, shopper):
    add(client, shopper, shop["m"], 3)
    client.patch(f"/api/admin/variants/{shop['m']}", json={"stock": 2}, headers=admin)
    address = new_address(client, shopper)
    res = client.post("/api/orders", json={"address_id": address["id"]}, headers=shopper)
    assert res.status_code == 409 and "Only 2" in res.json()["detail"]
    assert stock(shop["m"]) == 2


def test_orders_are_private(client, shop, shopper):
    add(client, shopper, shop["m"])
    address = new_address(client, shopper)
    number = client.post("/api/orders", json={"address_id": address["id"]}, headers=shopper).json()["number"]
    other = auth_header(signup(client, email="other@example.com")["access_token"])
    assert client.get(f"/api/orders/{number}", headers=other).status_code == 404


def test_last_unit_race_only_one_order_wins(client, shop):
    """Two shoppers check out the single XXL at the same moment: exactly one succeeds."""
    users = []
    for email in ("a@example.com", "b@example.com"):
        h = auth_header(signup(client, email=email)["access_token"])
        add(client, h, shop["xxl"])
        users.append(new_address(client, h)["id"])

    barrier = threading.Barrier(2)
    results = []

    def checkout(address_id):
        with SessionLocal() as db:
            address = db.get(Address, address_id)
            user = db.get(User, address.user_id)
            barrier.wait()
            try:
                order_service.place_order(db, user, address_id, None)
                results.append("ok")
            except HTTPException as e:
                results.append(e.status_code)

    threads = [threading.Thread(target=checkout, args=(a,)) for a in users]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results, key=str) == [409, "ok"]
    assert stock(shop["xxl"]) == 0


def test_limited_code_cannot_be_overused(client, admin, shop):
    make_discount(client, admin, code="ONCE", usage_limit=1)
    statuses = []
    for email in ("a@example.com", "b@example.com"):
        h = auth_header(signup(client, email=email)["access_token"])
        add(client, h, shop["m"])
        address = new_address(client, h)
        res = client.post("/api/orders", json={"address_id": address["id"], "discount_code": "ONCE"}, headers=h)
        statuses.append(res.status_code)
    assert statuses == [201, 422]  # second shopper is told the code is used up


# ---------------- cancel and expiry

def place(client, h, variant_id, qty=1, code=None):
    add(client, h, variant_id, qty)
    address = new_address(client, h)
    res = client.post("/api/orders", json={"address_id": address["id"], "discount_code": code}, headers=h)
    assert res.status_code == 201, res.text
    return res.json()["number"]


def test_customer_cancel_restores_stock_and_discount(client, admin, shop, shopper):
    make_discount(client, admin, code="SAVE")
    number = place(client, shopper, shop["m"], 2, "SAVE")
    assert stock(shop["m"]) == 3
    res = client.post(f"/api/orders/{number}/cancel", headers=shopper)
    assert res.json()["status"] == "cancelled"
    assert [e["status"] for e in res.json()["events"]] == ["pending_payment", "cancelled"]
    assert stock(shop["m"]) == 5
    assert client.get("/api/admin/discounts", headers=admin).json()[0]["used_count"] == 0
    assert client.post(f"/api/orders/{number}/cancel", headers=shopper).status_code == 409


def test_expire_job_cancels_only_overdue_orders(client, shop, shopper):
    old = place(client, shopper, shop["m"], 2)
    fresh = place(client, shopper, shop["dupatta"])
    with SessionLocal() as db:
        db.execute(update(Order).where(Order.number == old)
                   .values(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)))
        db.commit()
        assert order_service.expire_unpaid(db) == 1
        assert order_service.expire_unpaid(db) == 0  # idempotent
        statuses = dict(db.execute(select(Order.number, Order.status)).all())
    assert statuses == {old: "cancelled", fresh: "pending_payment"}
    assert stock(shop["m"]) == 5 and stock(shop["dupatta"]) == 1


def test_deleting_a_product_keeps_past_orders(client, admin, shop, shopper):
    number = place(client, shopper, shop["dupatta"])
    with SessionLocal() as db:
        product_id = db.get(Variant, shop["dupatta"]).product_id
    assert client.delete(f"/api/admin/products/{product_id}", headers=admin).status_code == 204
    item = client.get(f"/api/orders/{number}", headers=shopper).json()["items"][0]
    assert item["product_name"] == "Mul Dupatta" and item["product_id"] is None


def test_unused_discount_deleted_used_one_deactivated(client, admin, shop, shopper):
    unused = make_discount(client, admin, code="UNUSED")
    used = make_discount(client, admin, code="USED")
    place(client, shopper, shop["m"], 1, "USED")
    client.delete(f"/api/admin/discounts/{unused['id']}", headers=admin)
    client.delete(f"/api/admin/discounts/{used['id']}", headers=admin)
    with SessionLocal() as db:
        codes = {d.code: d.is_active for d in db.scalars(select(Discount))}
    assert codes == {"USED": False}
