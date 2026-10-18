from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.catalog.models import Product, Variant
from app.core.config import settings

from .models import CartItem
from .schemas import CartLine, CartOut


def _image_for(product: Product, colour: str) -> str | None:
    image = next((i for i in product.images if i.colour == colour), None) or next(iter(product.images), None)
    return image.url if image else None


def price_lines(db: Session, pairs: list[tuple[int, int]]) -> list[CartLine]:
    """Turn (variant_id, qty) pairs into priced lines using current prices and stock.

    Used for both server-side carts and guest carts, so every cart is priced the same way.
    Unknown variants are silently dropped.
    """
    if not pairs:
        return []
    variants = {
        v.id: v
        for v in db.scalars(
            select(Variant)
            .where(Variant.id.in_([vid for vid, _ in pairs]))
            .options(joinedload(Variant.product).selectinload(Product.images))
        )
    }
    lines = []
    for vid, qty in pairs:
        v = variants.get(vid)
        if v is None:
            continue
        sellable = v.is_active and v.product.is_active
        lines.append(
            CartLine(
                variant_id=v.id,
                qty=qty,
                product_id=v.product.id,
                product_name=v.product.name,
                product_slug=v.product.slug,
                image=_image_for(v.product, v.colour),
                size=v.size,
                colour=v.colour,
                sku=v.sku,
                unit_price=v.effective_price,
                line_total=v.effective_price * qty,
                stock=v.stock if sellable else 0,
                max_qty=min(v.stock, settings.max_qty_per_item) if sellable else 0,
                available=sellable and v.stock >= qty,
            )
        )
    return lines


def summarise(lines: list[CartLine]) -> CartOut:
    return CartOut(
        items=lines,
        item_count=sum(line.qty for line in lines),
        subtotal=sum(line.line_total for line in lines),
        shipping_fee=settings.shipping_fee,
        free_shipping_min=settings.free_shipping_min,
    )


def user_items(db: Session, user_id: int) -> list[CartItem]:
    return db.scalars(select(CartItem).where(CartItem.user_id == user_id).order_by(CartItem.id)).all()


def user_lines(db: Session, user_id: int) -> list[CartLine]:
    return price_lines(db, [(i.variant_id, i.qty) for i in user_items(db, user_id)])


def _sellable_variant(db: Session, variant_id: int) -> Variant:
    variant = db.scalar(select(Variant).where(Variant.id == variant_id).options(selectinload(Variant.product)))
    if variant is None or not variant.is_active or not variant.product.is_active:
        raise HTTPException(404, "This item is no longer available")
    if variant.stock == 0:
        raise HTTPException(409, "This size is out of stock")
    return variant


def set_qty(db: Session, user_id: int, variant_id: int, qty: int, add: bool = False) -> None:
    """Set (or add to) a line's quantity, capped at stock and the per-item limit. qty 0 removes it."""
    item = db.scalar(select(CartItem).where(CartItem.user_id == user_id, CartItem.variant_id == variant_id))
    new_qty = (item.qty if item and add else 0) + qty
    if new_qty <= 0:
        if item:
            db.delete(item)
        return
    variant = _sellable_variant(db, variant_id)
    new_qty = min(new_qty, variant.stock, settings.max_qty_per_item)
    if item:
        item.qty = new_qty
    else:
        db.add(CartItem(user_id=user_id, variant_id=variant_id, qty=new_qty))


def merge(db: Session, user_id: int, items) -> None:
    """Fold a guest cart into the user's cart; items that can't be added are skipped."""
    for it in items:
        try:
            set_qty(db, user_id, it.variant_id, it.qty, add=True)
        except HTTPException:
            continue


def clear(db: Session, user_id: int) -> None:
    for item in user_items(db, user_id):
        db.delete(item)
