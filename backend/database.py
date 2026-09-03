"""数据库初始化与会话管理"""
import logging
import re

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass


engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    future=True,
)


@event.listens_for(engine.sync_engine, "connect")
def _enable_sqlite_fk(dbapi_connection, connection_record):
    """SQLite 默认不启用外键约束，需要在每条连接上显式 PRAGMA。

    背景：ORM 上写的 ondelete="CASCADE" 只是 SQL 层声明，SQLite 默认关 FK 检查，
    导致级联删除形同虚设，删孩子时其他表会留孤儿数据。

    同时启用 WAL 模式 + synchronous=NORMAL，提升读写并发性能 3-5x
    （reader 不再被 writer 阻塞，崩溃安全性仍可接受）。
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA synchronous = NORMAL")
    cursor.close()

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """FastAPI 依赖：获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """初始化数据库表结构"""
    # 必须在导入 models 之后才能 create_all
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_data_quality(conn)
        await _migrate_wrong_question_bank_link(conn)
        await _migrate_exam_paper_analysis(conn)
        await _migrate_exercise_time_spent(conn)
        await _migrate_auth_foundation(conn)
        await _migrate_child_reward_status(conn)


async def _migrate_data_quality(conn) -> None:
    """存量库的数据质量迁移（幂等，每次启动都安全执行）。

    背景：create_all 对已存在的表不会补建新约束/索引，因此历史库缺少
    DB-1 / DB-2 的唯一性保障。此处先去重、再创建与 models.py 中
    同名的唯一索引（IF NOT EXISTS 保证与新建库不重复建索引）。

    - DB-1: child_ranks 同一 (child_id, subject) 只保留最早一行
    - DB-2: child_achievements 同一 (child_id, achievement_id, COALESCE(exam_id,-1))
            只保留最早一行（防止历史上已产生的重复授予）

    去重会真实删数据，因此逐表统计并写日志，便于事后追溯。
    """
    from sqlalchemy import text

    async def _dedupe(table: str, group_cols: str) -> int:
        """按 group_cols 分组去重，每组保留 id 最小的一行，返回被删行数。"""
        # 表名白名单（防止 SQL 注入）
        _ALLOWED_DEDUPE_TABLES = {"child_ranks", "child_achievements"}
        if table not in _ALLOWED_DEDUPE_TABLES:
            raise ValueError(f"不允许的去重表名：{table}")
        # group_cols 只允许列名、逗号、括号和 COALESCE 函数
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*(\s*,\s*[a-zA-Z_][a-zA-Z0-9_]*)*(\s*,\s*COALESCE\([^)]+\))?$', group_cols):
            raise ValueError(f"不允许的 group_cols：{group_cols}")
        before = (await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))).scalar_one()
        await conn.execute(text(
            f"DELETE FROM {table} WHERE id NOT IN "
            f"(SELECT MIN(id) FROM {table} GROUP BY {group_cols})"
        ))
        after = (await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))).scalar_one()
        removed = before - after
        if removed:
            logger.warning(
                "数据质量迁移：%s 清理重复行 %d 条（按 %s 分组，保留 id 最小者）",
                table, removed, group_cols,
            )
        return removed

    await _dedupe("child_ranks", "child_id, subject")
    await _dedupe("child_achievements", "child_id, achievement_id, COALESCE(exam_id, -1)")

    await conn.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_child_ranks_child_subject "
        "ON child_ranks(child_id, subject)"
    ))
    await conn.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_child_achievements_dedup "
        "ON child_achievements(child_id, achievement_id, COALESCE(exam_id, -1))"
    ))


async def _migrate_wrong_question_bank_link(conn) -> None:
    """WrongQuestion 加 bank_question_id 字段（智能匹配题库题目）。

    幂等：每次启动检测列是否存在，不存在则 ALTER TABLE ADD COLUMN + 建索引。
    """
    from sqlalchemy import text

    result = await conn.execute(
        text(
            "SELECT name FROM pragma_table_info('wrong_questions')"
            " WHERE name = 'bank_question_id'"
        )
    )
    if result.fetchone() is not None:
        return  # 已迁移过

    await conn.execute(
        text(
            "ALTER TABLE wrong_questions ADD COLUMN bank_question_id INTEGER "
            "REFERENCES questions(id) ON DELETE SET NULL"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_wrong_questions_bank_question_id "
            "ON wrong_questions(bank_question_id)"
        )
    )
    logger.info("迁移完成：wrong_questions.bank_question_id 已添加")


async def _migrate_exam_paper_analysis(conn) -> None:
    """考试表加纸面字段（paper_total_score / paper_actual_scored）。

    幂等：检测列是否存在。
    exam_questions 表由 Base.metadata.create_all 自动建。
    """
    from sqlalchemy import text

    for col in ("paper_total_score", "paper_actual_scored"):
        result = await conn.execute(
            text(
                "SELECT name FROM pragma_table_info('exams')"
                f" WHERE name = '{col}'"
            )
        )
        if result.fetchone() is not None:
            continue
        await conn.execute(
            text(f"ALTER TABLE exams ADD COLUMN {col} FLOAT")
        )
        logger.info("迁移完成：exams.%s 已添加", col)


async def _migrate_exercise_time_spent(conn) -> None:
    """exercises 表加 time_spent 字段（练习耗时，单位秒）。

    幂等：检测列是否存在，不存在则 ALTER TABLE ADD COLUMN。
    """
    from sqlalchemy import text

    result = await conn.execute(
        text("SELECT name FROM pragma_table_info('exercises') WHERE name = 'time_spent'")
    )
    if result.fetchone() is not None:
        return

    await conn.execute(
        text("ALTER TABLE exercises ADD COLUMN time_spent INTEGER")
    )
    logger.info("迁移完成：exercises.time_spent 已添加")


async def _migrate_child_reward_status(conn) -> None:
    """child_rewards 表加核销字段（status / used_at / used_by）。

    幂等：逐列检测，不存在才 ALTER TABLE ADD COLUMN。
    存量行默认 status='pending'（历史上兑换后无核销概念，视为待使用）。
    """
    from sqlalchemy import text

    cols = {
        "status": "VARCHAR(16) DEFAULT 'pending' NOT NULL",
        "used_at": "DATETIME",
        "used_by": "INTEGER",
    }
    for col, ddl in cols.items():
        result = await conn.execute(
            text(
                "SELECT name FROM pragma_table_info('child_rewards')"
                f" WHERE name = '{col}'"
            )
        )
        if result.fetchone() is not None:
            continue
        await conn.execute(
            text(f"ALTER TABLE child_rewards ADD COLUMN {col} {ddl}")
        )
        logger.info("迁移完成：child_rewards.%s 已添加", col)


async def _migrate_auth_foundation(conn) -> None:
    """v1.6.0 多用户认证迁移。

    幂等逻辑：
    1. families + users 表由 Base.metadata.create_all 自动建
    2. 检查 children.family_id 列是否存在，不存在则 ALTER TABLE ADD COLUMN
    3. 如果 families 表为空 → 建一个 "我的家" 默认家庭
    4. backfill: 把所有 family_id IS NULL 的孩子绑定到默认家庭
    """
    from sqlalchemy import text

    # 1. children.family_id 列（如果旧库没有则 ALTER 加）
    result = await conn.execute(
        text(
            "SELECT name FROM pragma_table_info('children')"
            " WHERE name = 'family_id'"
        )
    )
    if result.fetchone() is None:
        await conn.execute(
            text(
                "ALTER TABLE children ADD COLUMN family_id INTEGER "
                "REFERENCES families(id) ON DELETE CASCADE"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_children_family_id "
                "ON children(family_id)"
            )
        )
        logger.info("迁移完成：children.family_id 列已添加")

    # 2. 如果 families 表为空，建一个默认家庭
    family_count = (await conn.execute(text("SELECT COUNT(*) FROM families"))).scalar_one()
    if family_count == 0:
        await conn.execute(
            text(
                "INSERT INTO families (name, created_at) "
                "VALUES ('我的家', :now)"
            ),
            {"now": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)},
        )
        logger.info("迁移完成：默认家庭 '我的家' 已创建")

    # 3. backfill：把所有 family_id IS NULL 的孩子绑到默认家庭（id=1）
    null_kids = (await conn.execute(
        text("SELECT COUNT(*) FROM children WHERE family_id IS NULL")
    )).scalar_one()
    if null_kids > 0:
        await conn.execute(
            text("UPDATE children SET family_id = 1 WHERE family_id IS NULL")
        )
        logger.info("迁移完成：%d 个孩子的 family_id 已 backfill 到默认家庭", null_kids)
