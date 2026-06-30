"""项目配置"""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 基础路径
    BASE_DIR: Path = Path(__file__).parent.parent
    STATIC_DIR: Path = BASE_DIR / "static"
    UPLOAD_DIR: Path = BASE_DIR / "uploads"

    # 数据库
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/bookstore.db"

    # JWT 密钥（管理后台登录用）
    SECRET_KEY: str = "change-this-to-a-secure-random-string-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8小时

    # 微信小程序配置（以后对接）
    WX_APPID: str = ""
    WX_SECRET: str = ""
    WX_MCH_ID: str = ""  # 商户号
    WX_MCH_KEY: str = ""  # API密钥

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
