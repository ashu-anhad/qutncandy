import pytest

from .conftest import auth_header, make_admin, signup


@pytest.fixture
def admin(client):
    return make_admin(client)


@pytest.fixture
def catalog(client, admin):
    women = client.post("/api/admin/categories", json={"name": "Women"}, headers=admin).json()
    kurtas = client.post("/api/admin/categories", json={"name": "Kurtas", "parent_id": women["id"]}, headers=admin).json()
    men = client.post("/api/admin/categories", json={"name": "Men"}, headers=admin).json()

    def product(name, cat, price, variants, **extra):
        res = client.post(
            "/api/admin/products",
            json={"name": name, "category_id": cat["id"], "base_price": price, "variants": variants, **extra},
            headers=admin,
        )
        assert res.status_code == 201, res.text
        return res.json()

    noor = product("Noor Kurta", kurtas, 189000, [
        {"size": "M", "colour": "White", "stock": 3},
        {"size": "XXL", "colour": "White", "stock": 0, "price": 209000},
    ], description="Bakhiya work on the yoke")
    aftab = product("Aftab Men's Kurta", men, 199000, [{"size": "L", "colour": "Black", "stock": 5}])
    hidden = product("Hidden Draft", kurtas, 100000, [{"size": "M", "colour": "Mint", "stock": 1}], is_active=False)
    return {"women": women, "kurtas": kurtas, "men": men, "noor": noor, "aftab": aftab, "hidden": hidden}


def names(res):
    assert res.status_code == 200, res.text
    return [p["name"] for p in res.json()["items"]]


def test_public_list_hides_inactive_products(client, catalog):
    assert set(names(client.get("/api/products"))) == {"Noor Kurta", "Aftab Men's Kurta"}


def test_category_filter_includes_subcategories(client, catalog):
    assert names(client.get("/api/products?category=women")) == ["Noor Kurta"]
    assert client.get("/api/products?category=nope").status_code == 404


def test_size_colour_price_and_search_filters(client, catalog):
    assert names(client.get("/api/products?size=XXL")) == ["Noor Kurta"]
    assert names(client.get("/api/products?colour=black")) == ["Aftab Men's Kurta"]
    assert names(client.get("/api/products?max_price=190000")) == ["Noor Kurta"]
    assert names(client.get("/api/products?q=bakhiya")) == ["Noor Kurta"]


def test_sort_by_price(client, catalog):
    assert names(client.get("/api/products?sort=price_desc")) == ["Aftab Men's Kurta", "Noor Kurta"]


def test_product_detail(client, catalog):
    d = client.get("/api/products/noor-kurta").json()
    assert d["min_price"] == 189000 and d["max_price"] == 209000
    assert d["sizes"] == ["M", "XXL"]
    assert {v["effective_price"] for v in d["variants"]} == {189000, 209000}
    assert d["variants"][0]["sku"].startswith("QC-")
    assert client.get("/api/products/hidden-draft").status_code == 404


def test_filters_endpoint(client, catalog):
    f = client.get("/api/products/filters").json()
    assert f["sizes"] == ["M", "L", "XXL"]
    assert f["colours"] == ["Black", "White"]  # inactive product's Mint excluded
    assert (f["min_price"], f["max_price"]) == (189000, 209000)


def test_slugs_are_unique(client, admin, catalog):
    res = client.post("/api/admin/products", json={"name": "Noor Kurta", "category_id": catalog["men"]["id"],
                                                   "base_price": 1}, headers=admin)
    assert res.json()["slug"] == "noor-kurta-2"


def test_duplicate_variant_rejected(client, admin, catalog):
    res = client.post(f"/api/admin/products/{catalog['noor']['id']}/variants",
                      json={"size": "M", "colour": "White"}, headers=admin)
    assert res.status_code == 409


def test_update_variant_stock_and_price(client, admin, catalog):
    vid = catalog["noor"]["variants"][1]["id"]
    res = client.patch(f"/api/admin/variants/{vid}", json={"stock": 4, "price": None}, headers=admin)
    assert res.json()["stock"] == 4 and res.json()["effective_price"] == 189000
    assert client.patch(f"/api/admin/variants/{vid}", json={"stock": -1}, headers=admin).status_code == 422


def test_image_upload_and_delete(client, admin, catalog):
    pid = catalog["noor"]["id"]
    bad = client.post(f"/api/admin/products/{pid}/images", files={"file": ("x.svg", b"<svg/>", "image/svg+xml")},
                      headers=admin)
    assert bad.status_code == 415
    res = client.post(f"/api/admin/products/{pid}/images", files={"file": ("a.png", b"\x89PNG fake", "image/png")},
                      data={"colour": "White"}, headers=admin)
    assert res.status_code == 201
    image = res.json()
    assert client.get(image["url"]).content == b"\x89PNG fake"
    assert client.get("/api/products/noor-kurta").json()["image"] == image["url"]
    assert client.delete(f"/api/admin/images/{image['id']}", headers=admin).status_code == 204
    assert client.get(image["url"]).status_code == 404


def test_category_with_products_cannot_be_deleted(client, admin, catalog):
    assert client.delete(f"/api/admin/categories/{catalog['men']['id']}", headers=admin).status_code == 409
    assert client.delete(f"/api/admin/products/{catalog['aftab']['id']}", headers=admin).status_code == 204
    assert client.delete(f"/api/admin/categories/{catalog['men']['id']}", headers=admin).status_code == 204


def test_admin_list_includes_inactive(client, admin, catalog):
    res = client.get("/api/admin/products", headers=admin)
    assert res.json()["total"] == 3


def test_catalog_admin_requires_admin(client, catalog):
    token = signup(client, email="shopper@example.com")["access_token"]
    res = client.post("/api/admin/categories", json={"name": "X"}, headers=auth_header(token))
    assert res.status_code == 403
