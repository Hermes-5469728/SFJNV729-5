"""唯一数据库连接池 · src/core/database.py · 全平台仅此一处"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """依赖注入: FastAPI Depends(get_db) 获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """创建所有表（开发环境用，生产环境用 alembic）"""
    from src.core.base import Base
    import src.modules.medical.models  # noqa: 触发模型注册
    Base.metadata.create_all(bind=engine)
