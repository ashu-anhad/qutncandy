from pydantic import BaseModel, Field


class CartItemIn(BaseModel):
    variant_id: int
    qty: int = Field(default=1, ge=1, le=100)


class QtyIn(BaseModel):
    qty: int = Field(ge=0, le=100)


class GuestCartIn(BaseModel):
    items: list[CartItemIn] = Field(default=[], max_length=50)


class CartLine(BaseModel):
    variant_id: int
    qty: int
    product_id: int
    product_name: str
    product_slug: str
    image: str | None
    size: str
    colour: str
    sku: str
    unit_price: int
    line_total: int
    stock: int
    max_qty: int
    available: bool  # active, and enough stock for qty


class CartOut(BaseModel):
    items: list[CartLine]
    item_count: int
    subtotal: int
    shipping_fee: int
    free_shipping_min: int
