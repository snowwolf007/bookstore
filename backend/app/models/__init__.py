"""数据库模型"""
import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from ..database import Base


class Category(Base):
    """分类表 — 支持树形结构"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="分类名称")
    slug = Column(String(100), unique=True, index=True, comment="拼音/英文标识")
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True, comment="父分类ID")
    sort_order = Column(Integer, default=0, comment="排序")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # 父分类
    parent = relationship("Category", remote_side=[id], backref="children")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "parent_id": self.parent_id,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
        }


class Book(Base):
    """书刊表"""
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False, index=True, comment="书名（原样）")
    title_en = Column(String(300), default="", comment="英文书名")
    title_cn = Column(String(300), default="", comment="中文书名（自动从原样提取）")
    author = Column(String(300), default="", comment="作者")
    publisher = Column(String(200), default="", comment="出版社")
    isbn = Column(String(20), default="", comment="ISBN")
    year = Column(String(10), default="", comment="出版年份")
    price = Column(Float, default=0, comment="定价")
    stock = Column(Integer, default=0, comment="库存")
    description = Column(Text, default="", comment="简介")
    catalog_text = Column(Text, default="", comment="目录文本")

    # 封面图片路径
    cover_path = Column(String(300), default="", comment="封面图片相对路径")
    # 目录页图片（多张，JSON数组）
    catalog_images = Column(JSON, default=list, comment="目录页图片路径列表")

    # 分类
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    category = relationship("Category", backref="books")

    # 标签（JSON数组，如 ["建筑设计","进口原版"]）
    tags = Column(JSON, default=list)

    # 状态
    is_published = Column(Boolean, default=True, comment="上架")
    is_featured = Column(Boolean, default=False, comment="推荐")
    sort_order = Column(Integer, default=0, comment="排序")

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "title_en": self.title_en,
            "title_cn": self.title_cn,
            "author": self.author,
            "publisher": self.publisher,
            "isbn": self.isbn,
            "year": self.year,
            "price": self.price,
            "stock": self.stock,
            "description": self.description,
            "catalog_text": self.catalog_text,
            "cover_path": self.cover_path,
            "catalog_images": self.catalog_images or [],
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "",
            "tags": self.tags or [],
            "is_published": self.is_published,
            "is_featured": self.is_featured,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AdminUser(Base):
    """管理员"""
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    display_name = Column(String(100), default="管理员")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Order(Base):
    """订单表"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(50), unique=True, index=True, nullable=False, comment="订单号")
    wx_openid = Column(String(100), default="", comment="微信用户openid")
    total_amount = Column(Float, default=0, comment="总金额")
    status = Column(String(20), default="pending", comment="pending/paid/shipped/done/cancelled")
    recipient_name = Column(String(50), default="", comment="收件人")
    recipient_phone = Column(String(20), default="", comment="收件电话")
    recipient_address = Column(String(300), default="", comment="收货地址")
    remark = Column(String(500), default="", comment="备注")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)

    items = relationship("OrderItem", backref="order")


class OrderItem(Base):
    """订单明细"""
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    book_title = Column(String(300), default="", comment="下单时书名")
    price = Column(Float, default=0, comment="单价")
    quantity = Column(Integer, default=1)
    book = relationship("Book")
