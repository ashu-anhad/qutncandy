from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession

from . import service
from .schemas import CartItemIn, CartOut, GuestCartIn, QtyIn

router = APIRouter(prefix="/api/cart", tags=["cart"])


@router.get("", response_model=CartOut)
def get_cart(user: CurrentUser, db: DbSession):
    return service.summarise(service.user_lines(db, user.id))


@router.post("/items", response_model=CartOut)
def add_item(payload: CartItemIn, user: CurrentUser, db: DbSession):
    service.set_qty(db, user.id, payload.variant_id, payload.qty, add=True)
    db.commit()
    return get_cart(user, db)


@router.patch("/items/{variant_id}", response_model=CartOut)
def update_item(variant_id: int, payload: QtyIn, user: CurrentUser, db: DbSession):
    service.set_qty(db, user.id, variant_id, payload.qty)
    db.commit()
    return get_cart(user, db)


@router.delete("/items/{variant_id}", response_model=CartOut)
def remove_item(variant_id: int, user: CurrentUser, db: DbSession):
    service.set_qty(db, user.id, variant_id, 0)
    db.commit()
    return get_cart(user, db)


@router.post("/merge", response_model=CartOut)
def merge_guest_cart(payload: GuestCartIn, user: CurrentUser, db: DbSession):
    service.merge(db, user.id, payload.items)
    db.commit()
    return get_cart(user, db)


@router.post("/preview", response_model=CartOut)
def preview_guest_cart(payload: GuestCartIn, db: DbSession):
    """Prices a guest cart held in the browser. No login needed."""
    return service.summarise(service.price_lines(db, [(i.variant_id, i.qty) for i in payload.items]))
