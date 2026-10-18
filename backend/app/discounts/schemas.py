from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DiscountIn(BaseModel):
    code: str = Field(pattern=r"^[A-Za-z0-9_-]{3,40}$")
    type: Literal["percent", "flat"]
    value: int = Field(gt=0)
    min_order: int = Field(default=0, ge=0)
    max_discount: int | None = Field(default=None, gt=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    usage_limit: int | None = Field(default=None, ge=1)
    is_active: bool = True

    @model_validator(mode="after")
    def check(self):
        if self.type == "percent" and self.value > 100:
            raise ValueError("A percentage discount cannot exceed 100")
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("End date must be after the start date")
        return self


class DiscountUpdate(BaseModel):
    value: int | None = Field(default=None, gt=0)
    min_order: int | None = Field(default=None, ge=0)
    max_discount: int | None = Field(default=None, gt=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    usage_limit: int | None = Field(default=None, ge=1)
    is_active: bool | None = None


class DiscountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    type: str
    value: int
    min_order: int
    max_discount: int | None
    starts_at: datetime | None
    ends_at: datetime | None
    usage_limit: int | None
    used_count: int
    is_active: bool
    created_at: datetime
