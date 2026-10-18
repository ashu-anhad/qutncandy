import re
from dataclasses import dataclass, field

from fastapi import HTTPException
from sqlalchemy import Select, and_, distinct, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from .models import Category, Product, ProductImage, Variant
from .schemas import CatalogFilters, ProductCard, ProductDetail

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL", "3XL", "4XL", "Free Size"]
SORTS = ("newest", "price_asc", "price_desc", "rating")


def sort_sizes(sizes) -> list[str]:
    return sorted(set(sizes), key=lambda s: (SIZE_ORDER.index(s) if s in SIZE_ORDER else len(SIZE_ORDER), s))


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "item"


def unique_slug(db: Session, model, text: str, exclude_id: int | None = None) -> str:
    base = slugify(text)
    slug, n = base, 2
    while True:
        stmt = select(model.id).where(model.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(model.id != exclude_id)
        if db.scalar(stmt) is None:
            return slug
        slug, n = f"{base}-{n}", n + 1


def make_sku(product: Product, size: str, colour: str) -> str:
    return f"QC-{product.id}-{slugify(colour)[:12]}-{slugify(size)}".upper()


# ---- categories

def category_and_descendants(db: Session, slug: str) -> list[int]:
    cats = db.scalars(select(Category)).all()
    root = next((c for c in cats if c.slug == slug), None)
    if root is None:
        raise HTTPException(404, "Category not found")
    ids, frontier = [root.id], [root.id]
    while frontier:
        frontier = [c.id for c in cats if c.parent_id in frontier and c.id not in ids]
        ids += frontier
    return ids


# ---- product listing

def _min_price_subquery():
    effective = func.coalesce(Variant.price, Product.base_price)
    return (
        select(func.min(effective))
        .where(Variant.product_id == Product.id, Variant.is_active)
        .correlate(Product)
        .scalar_subquery()
    )


@dataclass
class ProductQuery:
    q: str | None = None
    category: str | None = None
    sizes: list[str] = field(default_factory=list)
    colours: list[str] = field(default_factory=list)
    min_price: int | None = None
    max_price: int | None = None
    sort: str = "newest"
    page: int = 1
    page_size: int = 24
    include_inactive: bool = False  # admin listings
    category_id: int | None = None


def _filtered(db: Session, f: ProductQuery) -> Select:
    min_price = _min_price_subquery()
    stmt = select(Product)
    if not f.include_inactive:
        stmt = stmt.where(Product.is_active, Product.variants.any(Variant.is_active))
    if f.q:
        like = f"%{f.q.strip()}%"
        stmt = stmt.where(or_(Product.name.ilike(like), Product.description.ilike(like)))
    if f.category:
        stmt = stmt.where(Product.category_id.in_(category_and_descendants(db, f.category)))
    if f.category_id:
        stmt = stmt.where(Product.category_id == f.category_id)
    variant_conds = [Variant.is_active]
    if f.sizes:
        variant_conds.append(Variant.size.in_(f.sizes))
    if f.colours:
        variant_conds.append(func.lower(Variant.colour).in_([c.lower() for c in f.colours]))
    if f.sizes or f.colours:
        stmt = stmt.where(Product.variants.any(and_(*variant_conds)))
    if f.min_price is not None:
        stmt = stmt.where(min_price >= f.min_price)
    if f.max_price is not None:
        stmt = stmt.where(min_price <= f.max_price)

    order = {
        "newest": [Product.created_at.desc(), Product.id.desc()],
        "price_asc": [min_price.asc().nulls_last(), Product.id],
        "price_desc": [min_price.desc().nulls_last(), Product.id],
        "rating": [Product.avg_rating.desc(), Product.review_count.desc(), Product.id],
    }[f.sort if f.sort in SORTS else "newest"]
    return stmt.order_by(*order)


def _with_relations(stmt: Select) -> Select:
    return stmt.options(
        joinedload(Product.category), selectinload(Product.variants), selectinload(Product.images)
    )


def list_products(db: Session, f: ProductQuery) -> dict:
    stmt = _filtered(db, f)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    products = db.scalars(_with_relations(stmt).offset((f.page - 1) * f.page_size).limit(f.page_size)).all()
    return {
        "items": [to_card(p, f.include_inactive) for p in products],
        "total": total,
        "page": f.page,
        "page_size": f.page_size,
    }


def get_product(db: Session, *, slug: str | None = None, product_id: int | None = None, admin=False) -> Product:
    stmt = _with_relations(select(Product))
    stmt = stmt.where(Product.slug == slug) if slug else stmt.where(Product.id == product_id)
    product = db.scalar(stmt)
    if product is None or (not admin and not product.is_active):
        raise HTTPException(404, "Product not found")
    return product


def filters(db: Session) -> CatalogFilters:
    live = and_(Variant.is_active, Product.is_active)
    sizes = db.scalars(select(distinct(Variant.size)).join(Product).where(live)).all()
    colours = db.scalars(select(distinct(Variant.colour)).join(Product).where(live)).all()
    effective = func.coalesce(Variant.price, Product.base_price)
    lo, hi = db.execute(
        select(func.min(effective), func.max(effective)).select_from(Variant).join(Product).where(live)
    ).one()
    return CatalogFilters(sizes=sort_sizes(sizes), colours=sorted(colours), min_price=lo, max_price=hi)


# ---- serialisation

def _visible_variants(p: Product, include_inactive: bool) -> list[Variant]:
    return p.variants if include_inactive else [v for v in p.variants if v.is_active]


def to_card(p: Product, include_inactive: bool = False) -> ProductCard:
    variants = _visible_variants(p, include_inactive)
    prices = [v.effective_price for v in variants]
    colours = list(dict.fromkeys(v.colour for v in variants))
    return ProductCard(
        id=p.id,
        name=p.name,
        slug=p.slug,
        category=p.category,
        min_price=min(prices) if prices else None,
        max_price=max(prices) if prices else None,
        image=p.images[0].url if p.images else None,
        colours=colours,
        avg_rating=p.avg_rating,
        review_count=p.review_count,
        in_stock=any(v.stock > 0 for v in variants if v.is_active),
        is_active=p.is_active,
        total_stock=sum(v.stock for v in variants),
    )


def to_detail(p: Product, include_inactive: bool = False) -> ProductDetail:
    variants = _visible_variants(p, include_inactive)
    return ProductDetail(
        **to_card(p, include_inactive).model_dump(),
        description=p.description,
        fabric=p.fabric,
        base_price=p.base_price,
        sizes=sort_sizes(v.size for v in variants),
        variants=variants,
        images=p.images,
    )


# ---- admin writes

def add_variant(db: Session, product: Product, data: dict) -> Variant:
    sku = data.pop("sku", None) or make_sku(product, data["size"], data["colour"])
    variant = Variant(product=product, sku=sku, **data)
    db.add(variant)
    return variant


def next_image_order(product: Product) -> int:
    return max((i.sort_order for i in product.images), default=-1) + 1


def add_image(db: Session, product: Product, url: str, colour: str | None) -> ProductImage:
    image = ProductImage(product_id=product.id, url=url, colour=colour, sort_order=next_image_order(product))
    db.add(image)
    return image
