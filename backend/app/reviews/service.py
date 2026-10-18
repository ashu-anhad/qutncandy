from fastapi import HTTPException
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.catalog.models import Product
from app.orders.models import Order, OrderItem

from .models import Review


def display_name(name: str) -> str:
    parts = name.split()
    return f"{parts[0]} {parts[1][0]}." if len(parts) > 1 else parts[0] if parts else "Customer"


def can_review(db: Session, user_id: int, product_id: int) -> bool:
    """Verified purchase: the customer has a delivered order containing this product."""
    return db.scalar(
        select(
            exists().where(
                OrderItem.product_id == product_id,
                OrderItem.order_id == Order.id,
                Order.user_id == user_id,
                Order.status == "delivered",
            )
        )
    )


def refresh_rating(db: Session, product_id: int) -> None:
    """Recompute the product's cached rating from approved reviews."""
    avg, count = db.execute(
        select(func.avg(Review.rating), func.count()).where(
            Review.product_id == product_id, Review.status == "approved"
        )
    ).one()
    product = db.get(Product, product_id)
    if product:
        product.avg_rating = round(float(avg), 2) if avg else 0
        product.review_count = count


def upsert(db: Session, user: User, product: Product, rating: int, title: str, comment: str) -> Review:
    if not can_review(db, user.id, product.id):
        raise HTTPException(403, "You can review products from your delivered orders.")
    review = db.scalar(select(Review).where(Review.product_id == product.id, Review.user_id == user.id))
    if review is None:
        review = Review(product_id=product.id, user_id=user.id)
        db.add(review)
    review.rating, review.title, review.comment = rating, title.strip(), comment.strip()
    review.status = "pending"  # every edit is re-moderated
    db.flush()
    refresh_rating(db, product.id)
    return review


def set_status(db: Session, review: Review, status: str) -> None:
    review.status = status
    db.flush()
    refresh_rating(db, review.product_id)
