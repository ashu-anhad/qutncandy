from pydantic import BaseModel


class CheckoutOptions(BaseModel):
    """Everything the browser needs to open the Razorpay popup."""

    key_id: str
    razorpay_order_id: str
    amount: int
    currency: str
    name: str
    description: str
    order_number: str
    prefill: dict


class VerifyIn(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
