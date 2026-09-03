"""教材 Big Task / Project 作品管理"""
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from dependencies import (
    assert_child_access,
    child_id_filter,
    get_accessible_child_ids,
    get_current_user,
)
from models import Child, ProjectWork, TextbookUnit, User
from schemas import OkResponse, ProjectWorkCreate, ProjectWorkOut, ProjectWorkUpdate

router = APIRouter(prefix="/api/project-works", tags=["项目作品"])


@router.get("", response_model=List[ProjectWorkOut])
async def list_works(
    child_id: Optional[int] = Query(None),
    unit_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    if child_id is not None:
        assert_child_access(accessible, child_id)
    stmt = select(ProjectWork).order_by(ProjectWork.submitted_at.desc())
    stmt = stmt.where(child_id_filter(accessible, child_id, ProjectWork.child_id))
    if unit_id:
        stmt = stmt.where(ProjectWork.unit_id == unit_id)
    if status:
        stmt = stmt.where(ProjectWork.status == status)
    result = await db.execute(stmt)
    return result.scalars().unique().all()


@router.post("", response_model=ProjectWorkOut, status_code=201)
async def submit_work(
    payload: ProjectWorkCreate,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    assert_child_access(accessible, payload.child_id)
    child = await db.get(Child, payload.child_id)
    if not child:
        raise HTTPException(404, "孩子不存在")
    unit = await db.get(TextbookUnit, payload.unit_id)
    if not unit:
        raise HTTPException(404, "教材单元不存在")
    pw = ProjectWork(**payload.model_dump())
    db.add(pw)
    await db.commit()
    await db.refresh(pw)
    return pw


@router.post("/{work_id}/upload", response_model=OkResponse)
async def upload_image(
    work_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    pw = await db.get(ProjectWork, work_id)
    if not pw:
        raise HTTPException(404, "作品不存在")
    assert_child_access(accessible, pw.child_id)
    # 存到本地 uploads/project_works/
    from pathlib import Path

    from config import settings

    # 1) 扩展名白名单（仅图片）
    ALLOWED_EXTS = {"jpg", "jpeg", "png", "webp", "gif"}
    raw_name = file.filename or ""
    ext = raw_name.rsplit(".", 1)[-1].lower() if "." in raw_name else ""
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, f"不支持的文件类型：.{ext}。仅允许 {sorted(ALLOWED_EXTS)}")

    # 2) MIME 类型二次校验（防扩展名伪造）
    ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if (file.content_type or "").lower() not in ALLOWED_MIMES:
        raise HTTPException(400, f"MIME 类型不被允许：{file.content_type}")

    # 3) 大小限制（读到上限就拒，避免 OOM）
    max_bytes = int(settings.max_upload_size_mb) * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(413, f"文件超过 {settings.max_upload_size_mb}MB 限制（实际 {len(content)/1024/1024:.1f}MB）")

    upload_dir = Path("./uploads/project_works")
    upload_dir.mkdir(parents=True, exist_ok=True)
    fname = f"work_{work_id}_{int(datetime.now(timezone.utc).timestamp())}.{ext}"
    target = upload_dir / fname
    with target.open("wb") as fh:
        fh.write(content)
    pw.image_path = f"/uploads/project_works/{fname}"
    await db.commit()
    return OkResponse(message="上传成功：" + pw.image_path)


@router.put("/{work_id}/review", response_model=ProjectWorkOut)
async def review_work(
    work_id: int,
    payload: ProjectWorkUpdate,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    pw = await db.get(ProjectWork, work_id)
    if not pw:
        raise HTTPException(404, "作品不存在")
    assert_child_access(accessible, pw.child_id)
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(pw, k, v)
    pw.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(pw)
    return pw


@router.delete("/{work_id}", response_model=OkResponse)
async def delete_work(
    work_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    pw = await db.get(ProjectWork, work_id)
    if not pw:
        raise HTTPException(404, "作品不存在")
    assert_child_access(accessible, pw.child_id)
    await db.delete(pw)
    await db.commit()
    return OkResponse(message="删除成功")


@router.get("/{work_id}/image")
async def get_work_image(
    work_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """鉴权回取作品图片（更稳妥的替代方案，避免 /uploads 静态目录公开暴露）。

    校验 child_id 归属后返回文件。前端既可用 <img src="/uploads/...">（静态挂载，家庭 LAN 可接受），
    也可用本端点（带 Bearer token，适合跨设备 / 严格隐私场景）。
    """
    pw = await db.get(ProjectWork, work_id)
    if not pw or not pw.image_path:
        raise HTTPException(404, "作品或图片不存在")
    assert_child_access(accessible, pw.child_id)
    fname = pw.image_path.rsplit("/", 1)[-1]
    base = Path(settings.upload_dir).resolve()
    target = (base / "project_works" / fname).resolve()
    # 防路径穿越：目标必须落在 upload_dir 内
    if not str(target).startswith(str(base)) or not target.is_file():
        raise HTTPException(404, "图片不存在")
    return FileResponse(target)
