from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.auth.models import User
from app.catalog.models import Product
from app.catalog.service import get_product
from app.core.deps import AdminUser, CurrentUser, DbSession
from app.core.errors import get_or_404

from . import service
from .models import Review
from .schemas import AdminReviewOut, MyReview, ReviewIn, ReviewPage

router = APIRouter(prefix="/api/products/{slug}/reviews", tags=["reviews"])
admin_router = APIRouter(prefix="/api/admin/reviews", tags=["admin: reviews"])


def _own(review: Review) -> dict:
    return {"id": review.id, "rating": review.rating, "title": review.title, "comment": review.comment,
            "status": review.status, "created_at": review.created_at}


@router.get("", response_model=ReviewPage)
def list_reviews(slug: str, db: DbSession, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50)):
    product = get_product(db, slug=slug)
    approved = (Review.product_id == product.id, Review.status == "approved")
    rows = db.execute(
        select(Review, User.name).join(User, User.id == Review.user_id).where(*approved)
        .order_by(Review.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    dist = dict(db.execute(select(Review.rating, func.count()).where(*approved).group_by(Review.rating)).all())
    return {
        "items": [
            {"id": r.id, "rating": r.rating, "title": r.title, "comment": r.comment,
             "author": service.display_name(name), "created_at": r.created_at}
            for r, name in rows
        ],
        "total": product.review_count,
        "page": page,
        "page_size": page_size,
        "avg_rating": product.avg_rating,
        "distribution": {stars: dist.get(stars, 0) for stars in range(5, 0, -1)},
    }


@router.get("/mine", response_model=MyReview)
def my_review(slug: str, user: CurrentUser, db: DbSession):
    product = get_product(db, slug=slug)
    review = db.scalar(select(Review).where(Review.product_id == product.id, Review.user_id == user.id))
    return {"can_review": service.can_review(db, user.id, product.id), "review": _own(review) if review else None}


@router.put("", response_model=MyReview)
def write_review(slug: str, payload: ReviewIn, user: CurrentUser, db: DbSession):
    product = get_product(db, slug=slug)
    review = service.upsert(db, user, product, payload.rating, payload.title, payload.comment)
    db.commit()
    db.refresh(review)
    return {"can_review": True, "review": _own(review)}


# =========================== admin ===========================

@admin_router.get("")
def admin_list_reviews(
    _: AdminUser, db: DbSession, status: str = "pending",
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
):
    base = (
        select(Review, Product, User)
        .join(Product, Product.id == Review.product_id)
        .join(User, User.id == Review.user_id)
        .where(Review.status == status)
    )
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    order = Review.created_at.asc() if status == "pending" else Review.created_at.desc()
    rows = db.execute(base.order_by(order).offset((page - 1) * page_size).limit(page_size)).all()
    items = [
        AdminReviewOut(id=r.id, rating=r.rating, title=r.title, comment=r.comment, status=r.status,
                       created_at=r.created_at, product_id=p.id, product_name=p.name, product_slug=p.slug,
                       customer_name=u.name, customer_email=u.email)
        for r, p, u in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@admin_router.post("/{review_id}/{action}", status_code=status.HTTP_204_NO_CONTENT)
def moderate(review_id: int, action: str, _: AdminUser, db: DbSession):
    new_status = {"approve": "approved", "reject": "rejected"}.get(action)
    if new_status is None:
        raise HTTPException(404, "Unknown action")
    service.set_status(db, get_or_404(db, Review, review_id, "Review"), new_status)
    db.commit()


@admin_router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(review_id: int, _: AdminUser, db: DbSession):
    review = get_or_404(db, Review, review_id, "Review")
    product_id = review.product_id
    db.delete(review)
    db.flush()
    service.refresh_rating(db, product_id)
    db.commit()
