"""Pydantic 数据模型"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ===== 分类 =====
class CategoryCreate(BaseModel):
    name: str
    slug: str
    parent_id: Optional[int] = None
    sort_order: int = 0


class CategoryOut(BaseModel):
    id: int
    name: str
    slug: str
    parent_id: Optional[int] = None
    sort_order: int
    is_active: bool

    class Config:
        from_attributes = True


class CategoryTree(CategoryOut):
    children: List["CategoryTree"] = []


# ===== 书刊 =====
class BookCreate(BaseModel):
    title: str
    title_en: str = ""
    title_cn: str = ""
    author: str = ""
    publisher: str = ""
    isbn: str = ""
    year: str = ""
    price: float = 0
    stock: int = 0
    description: str = ""
    catalog_text: str = ""
    category_id: Optional[int] = None
    tags: List[str] = []
    is_published: bool = True
    is_featured: bool = False


class BookUpdate(BaseModel):
    title: Optional[str] = None
    title_en: Optional[str] = None
    title_cn: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    isbn: Optional[str] = None
    year: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    description: Optional[str] = None
    catalog_text: Optional[str] = None
    cover_path: Optional[str] = None
    category_id: Optional[int] = None
    tags: Optional[List[str]] = None
    is_published: Optional[bool] = None
    is_featured: Optional[bool] = None


class BookOut(BaseModel):
    id: int
    title: str
    title_en: str
    title_cn: str
    author: str
    publisher: str
    isbn: str
    year: str
    price: float
    stock: int
    description: str
    catalog_text: str
    cover_path: str
    catalog_images: List[str]
    category_id: Optional[int]
    category_name: str
    tags: List[str]
    is_published: bool
    is_featured: bool
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class BookListOut(BaseModel):
    id: int
    title: str
    author: str
    publisher: str
    price: float
    isbn: str
    cover_path: str
    category_name: str
    is_published: bool
    created_at: Optional[str]

    class Config:
        from_attributes = True


# ===== 管理员 =====
class AdminLogin(BaseModel):
    username: str
    password: str


class AdminToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ===== 订单 =====
class OrderCreate(BaseModel):
    items: List[dict]  # [{"book_id": 1, "quantity": 1}, ...]
    recipient_name: str
    recipient_phone: str
    recipient_address: str
    remark: str = ""
