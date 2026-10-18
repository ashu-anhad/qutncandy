from datetime import datetime

from pydantic import BaseModel, Field


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    title: str = Field(default="", max_length=120)
    comment: str = Field(default="", max_length=2000)


class ReviewOut(BaseModel):
    id: int
    rating: int
    title: str
    comment: str
    author: str  # first name + initial
    created_at: datetime


class MyReview(BaseModel):
    can_review: bool  # has a delivered order containing this product
    review: dict | None  # own review incl. status, if written


class ReviewPage(BaseModel):
    items: list[ReviewOut]
    total: int
    page: int
    page_size: int
    avg_rating: float
    distribution: dict[int, int]  # stars -> count


class AdminReviewOut(BaseModel):
    id: int
    rating: int
    title: str
    comment: str
    status: str
    created_at: datetime
    product_id: int
    product_name: str
    product_slug: str
    customer_name: str
    customer_email: str | None
