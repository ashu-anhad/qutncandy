from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


# ---- categories

class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str | None = Field(default=None, max_length=120)
    parent_id: int | None = None
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    parent_id: int | None = None
    sort_order: int | None = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    parent_id: int | None
    sort_order: int


class CategoryRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


# ---- variants and images

class VariantIn(BaseModel):
    size: str = Field(min_length=1, max_length=20)
    colour: str = Field(min_length=1, max_length=40)
    sku: str | None = Field(default=None, max_length=64)
    price: int | None = Field(default=None, ge=0)
    stock: int = Field(default=0, ge=0)
    is_active: bool = True


class VariantUpdate(BaseModel):
    size: str | None = Field(default=None, min_length=1, max_length=20)
    colour: str | None = Field(default=None, min_length=1, max_length=40)
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    price: int | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class VariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    size: str
    colour: str
    price: int | None
    effective_price: int
    stock: int
    is_active: bool


class ImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    colour: str | None
    sort_order: int


# ---- products

class ProductIn(BaseModel):
    category_id: int
    name: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=220)
    description: str = ""
    fabric: str = Field(default="Cotton", max_length=100)
    base_price: int = Field(ge=0)
    is_active: bool = True
    variants: list[VariantIn] = []


class ProductUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    slug: str | None = Field(default=None, min_length=1, max_length=220)
    description: str | None = None
    fabric: str | None = Field(default=None, max_length=100)
    base_price: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ProductCard(BaseModel):
    id: int
    name: str
    slug: str
    category: CategoryRef
    min_price: int | None
    max_price: int | None
    image: str | None
    colours: list[str]
    avg_rating: float
    review_count: int
    in_stock: bool
    is_active: bool
    total_stock: int


class ProductDetail(ProductCard):
    description: str
    fabric: str
    base_price: int
    sizes: list[str]
    variants: list[VariantOut]
    images: list[ImageOut]


class CatalogFilters(BaseModel):
    sizes: list[str]
    colours: list[str]
    min_price: int | None
    max_price: int | None
