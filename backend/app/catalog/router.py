from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.core.deps import AdminUser, DbSession
from app.core.errors import commit_or_409, get_or_404
from app.core.storage import delete_file, save_file

from . import service
from .models import Category, Product, ProductImage, Variant
from .schemas import (
    CatalogFilters,
    CategoryIn,
    CategoryOut,
    CategoryUpdate,
    ImageOut,
    Page,
    ProductCard,
    ProductDetail,
    ProductIn,
    ProductUpdate,
    VariantIn,
    VariantOut,
    VariantUpdate,
)

router = APIRouter(prefix="/api", tags=["catalog"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin: catalog"])

IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


# =========================== storefront ===========================

@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: DbSession):
    return db.scalars(select(Category).order_by(Category.sort_order, Category.name)).all()


@router.get("/products", response_model=Page[ProductCard])
def list_products(
    db: DbSession,
    q: str | None = None,
    category: str | None = None,
    size: Annotated[list[str], Query()] = [],
    colour: Annotated[list[str], Query()] = [],
    min_price: int | None = Query(None, ge=0),
    max_price: int | None = Query(None, ge=0),
    sort: str = "newest",
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=60),
):
    return service.list_products(
        db,
        service.ProductQuery(
            q=q, category=category, sizes=size, colours=colour, min_price=min_price,
            max_price=max_price, sort=sort, page=page, page_size=page_size,
        ),
    )


@router.get("/products/filters", response_model=CatalogFilters)
def product_filters(db: DbSession):
    return service.filters(db)


@router.get("/products/{slug}", response_model=ProductDetail)
def product_detail(slug: str, db: DbSession):
    return service.to_detail(service.get_product(db, slug=slug))


# =========================== admin: categories ===========================

@admin_router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryIn, _: AdminUser, db: DbSession):
    data = payload.model_dump()
    data["slug"] = service.unique_slug(db, Category, data["slug"] or data["name"])
    category = Category(**data)
    db.add(category)
    commit_or_409(db, "Category already exists")
    db.refresh(category)
    return category


@admin_router.patch("/categories/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, payload: CategoryUpdate, _: AdminUser, db: DbSession):
    category = get_or_404(db, Category, category_id, "Category")
    data = payload.model_dump(exclude_unset=True)
    if data.get("parent_id") == category_id:
        raise HTTPException(422, "A category cannot be its own parent")
    if data.get("slug"):
        data["slug"] = service.slugify(data["slug"])
    for k, v in data.items():
        setattr(category, k, v)
    commit_or_409(db, "Slug already in use")
    db.refresh(category)
    return category


@admin_router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, _: AdminUser, db: DbSession):
    category = get_or_404(db, Category, category_id, "Category")
    if db.scalar(select(func.count()).where(Product.category_id == category_id)):
        raise HTTPException(409, "Move or delete this category's products first")
    db.delete(category)
    db.commit()


# =========================== admin: products ===========================

@admin_router.get("/products", response_model=Page[ProductCard])
def admin_list_products(
    _: AdminUser,
    db: DbSession,
    q: str | None = None,
    category_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return service.list_products(
        db,
        service.ProductQuery(q=q, category_id=category_id, page=page, page_size=page_size, include_inactive=True),
    )


@admin_router.get("/products/{product_id}", response_model=ProductDetail)
def admin_get_product(product_id: int, _: AdminUser, db: DbSession):
    return service.to_detail(service.get_product(db, product_id=product_id, admin=True), include_inactive=True)


@admin_router.post("/products", response_model=ProductDetail, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductIn, _: AdminUser, db: DbSession):
    get_or_404(db, Category, payload.category_id, "Category")
    data = payload.model_dump(exclude={"variants"})
    data["slug"] = service.unique_slug(db, Product, data["slug"] or data["name"])
    product = Product(**data)
    db.add(product)
    db.flush()  # assigns product.id for generated SKUs
    for v in payload.variants:
        service.add_variant(db, product, v.model_dump())
    commit_or_409(db, "Duplicate variant (same size and colour) or SKU")
    return admin_get_product(product.id, _, db)


@admin_router.patch("/products/{product_id}", response_model=ProductDetail)
def update_product(product_id: int, payload: ProductUpdate, _: AdminUser, db: DbSession):
    product = get_or_404(db, Product, product_id, "Product")
    data = payload.model_dump(exclude_unset=True)
    if "category_id" in data:
        get_or_404(db, Category, data["category_id"], "Category")
    if data.get("slug"):
        data["slug"] = service.unique_slug(db, Product, data["slug"], exclude_id=product_id)
    for k, v in data.items():
        setattr(product, k, v)
    db.commit()
    return admin_get_product(product_id, _, db)


@admin_router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, _: AdminUser, db: DbSession):
    product = service.get_product(db, product_id=product_id, admin=True)
    urls = [i.url for i in product.images]
    db.delete(product)
    db.commit()
    for url in urls:
        delete_file(url)


# =========================== admin: variants ===========================

@admin_router.post("/products/{product_id}/variants", response_model=VariantOut, status_code=status.HTTP_201_CREATED)
def create_variant(product_id: int, payload: VariantIn, _: AdminUser, db: DbSession):
    product = get_or_404(db, Product, product_id, "Product")
    variant = service.add_variant(db, product, payload.model_dump())
    commit_or_409(db, "This size and colour (or SKU) already exists")
    db.refresh(variant)
    return variant


@admin_router.patch("/variants/{variant_id}", response_model=VariantOut)
def update_variant(variant_id: int, payload: VariantUpdate, _: AdminUser, db: DbSession):
    variant = get_or_404(db, Variant, variant_id, "Variant")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(variant, k, v)
    commit_or_409(db, "This size and colour (or SKU) already exists")
    db.refresh(variant)
    return variant


@admin_router.delete("/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_variant(variant_id: int, _: AdminUser, db: DbSession):
    db.delete(get_or_404(db, Variant, variant_id, "Variant"))
    db.commit()


# =========================== admin: images ===========================

@admin_router.post("/products/{product_id}/images", response_model=ImageOut, status_code=status.HTTP_201_CREATED)
async def upload_image(
    product_id: int,
    _: AdminUser,
    db: DbSession,
    file: UploadFile = File(...),
    colour: str | None = Form(None),
):
    product = service.get_product(db, product_id=product_id, admin=True)
    ext = IMAGE_TYPES.get(file.content_type or "")
    if ext is None:
        raise HTTPException(415, "Upload a JPEG, PNG or WebP image")
    data = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Image must be under {settings.max_upload_mb} MB")
    image = service.add_image(db, product, save_file(data, "products", ext), colour or None)
    db.commit()
    db.refresh(image)
    return image


@admin_router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(image_id: int, _: AdminUser, db: DbSession):
    image = get_or_404(db, ProductImage, image_id, "Image")
    url = image.url
    db.delete(image)
    db.commit()
    delete_file(url)


# =========================== admin: inventory ===========================

@admin_router.get("/inventory")
def inventory(
    _: AdminUser,
    db: DbSession,
    filter: str = "all",
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Every variant with its stock; `filter` = all | low | out. Lowest stock first."""
    base = select(Variant).join(Product)
    if filter == "low":
        base = base.where(Variant.stock > 0, Variant.stock <= settings.low_stock_threshold)
    elif filter == "out":
        base = base.where(Variant.stock == 0)
    if filter in ("low", "out"):
        base = base.where(Variant.is_active, Product.is_active)
    if q:
        like = f"%{q.strip()}%"
        base = base.where(or_(Product.name.ilike(like), Variant.sku.ilike(like), Variant.colour.ilike(like)))
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    variants = db.scalars(
        base.options(joinedload(Variant.product))
        .order_by(Variant.stock, Product.name, Variant.colour, Variant.size)
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [
            {"id": v.id, "product_id": v.product_id, "product_name": v.product.name, "sku": v.sku, "size": v.size,
             "colour": v.colour, "stock": v.stock, "is_active": v.is_active and v.product.is_active}
            for v in variants
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "low_stock_threshold": settings.low_stock_threshold,
    }
