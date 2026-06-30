"""管理员认证"""
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.hash import sha256_crypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models import AdminUser
from ..schemas import AdminLogin, AdminToken

router = APIRouter(prefix="/api/admin", tags=["管理后台"])
security = HTTPBearer()


def verify_password(plain: str, hashed: str) -> bool:
    return sha256_crypt.verify(plain, hashed)


def get_password_hash(password: str) -> str:
    return sha256_crypt.hash(password)


def create_token(user_id: int, username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "username": username, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get("sub", 0))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="无效的认证令牌")

    result = await db.execute(select(AdminUser).where(AdminUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user


@router.post("/login", response_model=AdminToken)
async def login(data: AdminLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AdminUser).where(AdminUser.username == data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_token(user.id, user.username)
    return AdminToken(access_token=token)


@router.get("/me")
async def get_me(user: AdminUser = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "display_name": user.display_name}


# 初始化默认管理员（首次运行时调用）
async def init_admin(db: AsyncSession):
    result = await db.execute(select(AdminUser).where(AdminUser.username == "admin"))
    if not result.scalar_one_or_none():
        admin = AdminUser(
            username="admin",
            hashed_password=get_password_hash("admin123"),
            display_name="管理员",
        )
        db.add(admin)
        await db.commit()
