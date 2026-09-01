"""pytest 公共 fixtures：异步内存 DB + session + 依赖覆盖"""
import asyncio
import pathlib

# 让 backend/ 在 sys.path 里（pytest.ini 的 rootpath = backend/）
import sys

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from database import Base
from models import *  # noqa: F403  — 确保所有模型注册到 Base.metadata
from models import Child, Exam  # 显式导入，供下方工厂使用


@pytest.fixture(scope="session")
def event_loop():
    """整个 test session 共用一个 event loop，避免每个 fixture 各建一个。"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def engine():
    """每个测试函数一个独立的内存数据库。"""
    eng = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # 启用外键（和 production database.py 保持一致）
    from sqlalchemy import event

    @event.listens_for(eng.sync_engine, "connect")
    def _set_fk(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(engine):
    """提供一个会在测试结束后 rollback 的 session。"""
    session_factory = async_sessionmaker(engine, class_=AsyncSession,
                                         expire_on_commit=False, autoflush=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


# ---------- 常用工厂 helpers ----------

@pytest_asyncio.fixture
async def make_child(db_session):
    """返回一个 async 工厂：create_child(name=..., grade=...) -> Child"""
    async def _create(name="测试娃", grade="四年级", **kw):
        child = Child(name=name, grade=grade, **kw)
        db_session.add(child)
        await db_session.flush()
        return child
    return _create


@pytest_asyncio.fixture
async def make_exam(db_session):
    """create_exam(child_id, subject, score, full_score, exam_name, exam_date) -> Exam"""
    from datetime import date as date_cls
    async def _create(child_id, subject="数学", score=90, full_score=100,
                      exam_name="单元测试", exam_date=None, **kw):
        exam = Exam(
            child_id=child_id, subject=subject,
            score=score, full_score=full_score,
            exam_name=exam_name, exam_date=exam_date or date_cls.today(),
            **kw,
        )
        db_session.add(exam)
        await db_session.flush()
        return exam
    return _create
