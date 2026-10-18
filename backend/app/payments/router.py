import json

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from app.core.deps import CurrentUser, DbSession
from app.orders import service as order_service
from app.orders.schemas import OrderOut

from . import service
from .schemas import CheckoutOptions, VerifyIn

router = APIRouter(prefix="/api", tags=["payments"])


@router.post("/orders/{number}/pay", response_model=CheckoutOptions)
def start_payment(number: str, user: CurrentUser, db: DbSession):
    order = order_service.get_order(db, number, user, lock=True)
    return service.start_payment(db, order, user)


@router.post("/payments/verify", response_model=OrderOut)
def verify_payment(payload: VerifyIn, user: CurrentUser, db: DbSession, tasks: BackgroundTasks):
    """Called by the browser right after the Razorpay popup reports success."""
    if not service.enabled() or not service.valid_payment_signature(
        payload.razorpay_order_id, payload.razorpay_payment_id, payload.razorpay_signature
    ):
        raise HTTPException(400, "We couldn't verify this payment. If money was debited, it will be confirmed shortly.")
    order = service.record_payment(db, payload.razorpay_order_id, payload.razorpay_payment_id, tasks)
    if order is None or order.user_id != user.id:
        raise HTTPException(404, "Order not found")
    return order_service.get_order(db, order.number, user)


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request, db: DbSession, tasks: BackgroundTasks, x_razorpay_signature: str = Header(default="")
):
    """Razorpay's server-to-server notice; the source of truth if the browser never comes back."""
    body = await request.body()
    if not service.valid_webhook_signature(body, x_razorpay_signature):
        raise HTTPException(400, "Invalid signature")
    event = json.loads(body)
    if event.get("event") in ("payment.captured", "order.paid"):
        payment = event["payload"]["payment"]["entity"]
        if payment.get("order_id"):
            service.record_payment(db, payment["order_id"], payment["id"], tasks, payment.get("amount"))
    return {"status": "ok"}
