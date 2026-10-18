from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.cart.schemas import CartLine


class QuoteIn(BaseModel):
    discount_code: str | None = Field(default=None, max_length=40)


class QuoteOut(BaseModel):
    items: list[CartLine]
    subtotal: int
    discount: int
    discount_code: str | None  # set only when the code applied
    discount_error: str | None
    shipping_fee: int
    total: int
    can_place: bool
    problems: list[str]


class PlaceOrderIn(BaseModel):
    address_id: int
    discount_code: str | None = Field(default=None, max_length=40)


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int | None
    product_name: str
    product_slug: str
    size: str
    colour: str
    sku: str
    image: str | None
    unit_price: int
    qty: int
    line_total: int


class OrderEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    note: str
    created_at: datetime


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    number: str
    status: str
    created_at: datetime
    expires_at: datetime | None
    subtotal: int
    discount: int
    discount_code: str | None
    shipping_fee: int
    total: int
    address: dict
    courier: str | None
    tracking_no: str | None
    refund_status: str | None
    items: list[OrderItemOut]
    events: list[OrderEventOut]


class OrderSummary(BaseModel):
    number: str
    status: str
    created_at: datetime
    total: int
    item_count: int
    image: str | None


# ---- admin

class ShipIn(BaseModel):
    courier: str = Field(min_length=1, max_length=100)
    tracking_no: str = Field(min_length=1, max_length=100)
    note: str = Field(default="", max_length=500)


class NoteIn(BaseModel):
    note: str = Field(default="", max_length=500)


class CustomerRef(BaseModel):
    id: int
    name: str
    email: str | None
    phone: str | None


class AdminOrderOut(OrderOut):
    customer: CustomerRef
    razorpay_order_id: str | None
    razorpay_payment_id: str | None


class AdminOrderSummary(OrderSummary):
    customer_name: str
    customer_email: str | None
    refund_status: str | None
