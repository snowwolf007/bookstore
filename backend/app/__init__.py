"""FastAPI 主入口"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：初始化数据库 + 默认管理员
    await init_db()
    async for db in get_db():
        from .routers.auth import init_admin
        await init_admin(db)
        break
    yield
    # 关闭时：无需操作


app = FastAPI(
    title="建筑书店 API",
    description="厦门建筑书店独立站后台服务",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — 允许管理后台跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件（上传的图片）
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")

# 管理后台静态页面
STATIC_HTML = settings.STATIC_DIR / "admin.html"
if STATIC_HTML.exists():
    app.mount("/admin", StaticFiles(directory=str(settings.STATIC_DIR), html=True), name="admin")

# 导入路由
from .routers.auth import router as auth_router
from .routers.books import router as admin_book_router
from .routers.books import public_router as public_book_router

app.include_router(auth_router)
app.include_router(admin_book_router)
app.include_router(public_book_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
