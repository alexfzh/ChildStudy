"""审计报告（2026-09-03）修复项回归测试

覆盖：
- [High] 默认 JWT 占位密钥启动即 fail-fast
- [Low]  服务端登出 / 令牌吊销（RevokedToken）
- [P1]   考试创建后自动发积分（grant_exam_reward）
"""
from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from config import DEFAULT_JWT_SECRET, Settings
from dependencies import get_current_user
from models import PointsLog, RevokedToken, User
from routers.exams import create_exam
from routers.rewards import calc_exam_points
from schemas import ExamCreate
from utils.security import create_jwt, decode_jwt

# ============ [High] 默认密钥 fail-fast ============

def test_settings_rejects_default_placeholder_secret():
    """JWT_SECRET 仍为公开占位值时应直接拒绝启动（防止伪造任意角色 token）。"""
    with pytest.raises(ValueError):
        Settings(jwt_secret=DEFAULT_JWT_SECRET)


def test_settings_accepts_strong_secret():
    """强随机密钥（≥32）可正常实例化。"""
    s = Settings(jwt_secret="x" * 40)
    assert s.jwt_secret == "x" * 40


# ============ [Low] 令牌吊销 ============

async def test_revoked_token_rejected(db_session):
    """登出（写入 RevokedToken）后，旧 token 立即失效，get_current_user 返回 401。"""
    from config import settings
    from models import Family

    db_session.add(Family(id=1, name="测试家"))
    user = User(
        id=1, username="revoke_test", password_hash="x", display_name="测试",
        role="parent", family_id=1, is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    token = create_jwt(
        {"sub": 1, "role": "parent", "family_id": 1},
        settings.jwt_secret, 3600,
    )
    # 吊销前：有效
    u = await get_current_user(authorization=f"Bearer {token}", db=db_session)
    assert u.id == 1

    # 模拟 /api/auth/logout 写入吊销记录
    jti = decode_jwt(token, settings.jwt_secret).get("jti")
    assert jti
    db_session.add(RevokedToken(jti=jti))
    await db_session.commit()

    # 吊销后：401
    with pytest.raises(HTTPException) as exc:
        await get_current_user(authorization=f"Bearer {token}", db=db_session)
    assert exc.value.status_code == 401


# ============ [P1] 考试自动发积分 ============

async def test_create_exam_auto_grants_points(db_session, make_child):
    """创建考试成功后应自动发放 exam_reward 积分（幂等核心逻辑）。"""
    child = await make_child()
    payload = ExamCreate(
        child_id=child.id, subject="数学", exam_name="单元测试",
        score=90, full_score=100, exam_date=date.today(),
    )
    exam = await create_exam(payload, db_session)

    log = (await db_session.execute(
        select(PointsLog).where(
            PointsLog.child_id == child.id,
            PointsLog.source == "exam_reward",
            PointsLog.source_id == exam.id,
        )
    )).scalar_one_or_none()
    assert log is not None
    assert log.points == calc_exam_points(90, 100)


async def test_create_exam_auto_reward_idempotent(db_session, make_child):
    """自动发分与手动 /exam-reward 共用核心逻辑：重复触发不会产生双倍积分。"""
    from routers.rewards import grant_exam_reward

    child = await make_child()
    payload = ExamCreate(
        child_id=child.id, subject="语文", exam_name="月考",
        score=80, full_score=100, exam_date=date.today(),
    )
    exam = await create_exam(payload, db_session)  # 首次自动发分

    # 再次手动调用核心逻辑（模拟 backfill / 重复触发）
    await grant_exam_reward(db_session, exam.id)

    logs = (await db_session.execute(
        select(PointsLog).where(
            PointsLog.child_id == child.id,
            PointsLog.source == "exam_reward",
            PointsLog.source_id == exam.id,
        )
    )).scalars().all()
    assert len(logs) == 1  # 仍只一条，未双倍发分


# ============ [P0#2] CSV 导入行数限制 ============

async def test_csv_import_rejects_too_many_rows(db_session, make_child):
    """上传超过 max_import_rows 行的 CSV 应该直接 413拒绝，避免全文件读完后才报错."""
    from io import BytesIO

    from fastapi import HTTPException
    from starlette.datastructures import UploadFile

    from config import settings
    from routers.import_export import import_exams

    # 生成一个超限的 CSV：max_import_rows + 5 行
    lines = ["subject,exam_name,score,exam_date"]
    for i in range(settings.max_import_rows + 5):
        lines.append(f"数学,第{i}次单元测,90,2026-09-03")
    csv_bytes = ("\n".join(lines)).encode("utf-8-sig")

    upload = UploadFile(filename="big.csv", file=BytesIO(csv_bytes))

    child = await make_child()
    with pytest.raises(HTTPException) as exc:
        await import_exams(file=upload, child_id=child.id, db=db_session, accessible={child.id})
    assert exc.value.status_code == 413
    assert "超过限制" in str(exc.value.detail)


async def test_csv_import_accepts_under_limit(db_session, make_child):
    """限制内的 CSV 能正常导入 (回归保护，防止过检后阻挡正常文件)."""
    from io import BytesIO

    from starlette.datastructures import UploadFile

    from config import settings
    from routers.import_export import import_exams

    # 限制以下（默认 5000）
    row_count = min(50, settings.max_import_rows - 1)
    lines = ["subject,exam_name,score,exam_date"]
    for i in range(row_count):
        lines.append(f"数学,第{i}次练习,90,2026-09-03")
    csv_bytes = ("\n".join(lines)).encode("utf-8-sig")

    upload = UploadFile(filename="ok.csv", file=BytesIO(csv_bytes))

    child = await make_child()
    result = await import_exams(file=upload, child_id=child.id, db=db_session, accessible={child.id})
    assert "成功导入" in result.message

