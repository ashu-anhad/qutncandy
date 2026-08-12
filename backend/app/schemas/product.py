from pydantic import BaseModel, Field


class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    price: float = Field(..., gt=0)
    image_url: str | None = None
    category: str | None = None


class ProductCreate(ProductBase):
    pass


class ProductRead(ProductBase):
    id: int

    class Config:
        from_attributes = True
