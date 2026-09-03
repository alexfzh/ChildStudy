"""数据导入/导出路由"""
import csv
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import assert_child_access, child_id_filter, get_accessible_child_ids
from models import Child, Exam, Homework
from schemas import ExamCreate, HomeworkCreate, OkResponse

router = APIRouter(prefix="/api/import-export", tags=["导入导出"])


# ============ 导出 ============

@router.get("/exams")
async def export_exams(
    child_id: Optional[int] = None,
    subject: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """导出考试记录为 CSV"""
    if child_id is not None:
        assert_child_access(accessible, child_id)
    stmt = select(Exam).order_by(Exam.exam_date.desc(), Exam.id.desc())
    stmt = stmt.where(child_id_filter(accessible, child_id, Exam.child_id))
    if subject:
        stmt = stmt.where(Exam.subject == subject)
    if start_date:
        stmt = stmt.where(Exam.exam_date >= start_date)
    if end_date:
        stmt = stmt.where(Exam.exam_date <= end_date)
    result = await db.execute(stmt)
    exams = list(result.scalars().all())

    # 构建 CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "child_id", "subject", "exam_name", "exam_type", "score", "full_score",
        "class_rank", "grade_rank", "exam_date", "knowledge_points", "wrong_questions",
        "teacher_comment", "note", "grade_snapshot", "class_average"
    ])
    for e in exams:
        writer.writerow([
            e.id,
            e.child_id,
            e.subject,
            e.exam_name,
            e.exam_type,
            e.score,
            e.full_score,
            e.class_rank or "",
            e.grade_rank or "",
            e.exam_date.isoformat(),
            "|".join(e.knowledge_points or []),
            e.wrong_questions or "",
            e.teacher_comment or "",
            e.note or "",
            e.grade_snapshot or "",
            e.class_average if e.class_average is not None else "",
        ])

    from fastapi.responses import StreamingResponse
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=exams.csv"},
    )


@router.get("/homeworks")
async def export_homeworks(
    child_id: Optional[int] = None,
    subject: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """导出作业记录为 CSV"""
    if child_id is not None:
        assert_child_access(accessible, child_id)
    stmt = select(Homework).order_by(Homework.homework_date.desc(), Homework.id.desc())
    stmt = stmt.where(child_id_filter(accessible, child_id, Homework.child_id))
    if subject:
        stmt = stmt.where(Homework.subject == subject)
    if start_date:
        stmt = stmt.where(Homework.homework_date >= start_date)
    if end_date:
        stmt = stmt.where(Homework.homework_date <= end_date)
    result = await db.execute(stmt)
    homeworks = list(result.scalars().all())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "child_id", "subject", "title", "homework_date", "duration_minutes",
        "total_questions", "correct_questions", "accuracy", "completed", "difficulty", "note", "grade_snapshot"
    ])
    for h in homeworks:
        writer.writerow([
            h.id,
            h.child_id,
            h.subject,
            h.title,
            h.homework_date.isoformat(),
            h.duration_minutes or "",
            h.total_questions or "",
            h.correct_questions or "",
            h.accuracy if h.accuracy is not None else "",
            "true" if h.completed else "false",
            h.difficulty,
            h.note or "",
            h.grade_snapshot or "",
        ])

    from fastapi.responses import StreamingResponse
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=homeworks.csv"},
    )


# ============ 导入 ============

@router.post("/exams", response_model=OkResponse)
async def import_exams(
    file: UploadFile = File(...),
    child_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """上传考试 CSV 批量导入

    支持两种模式：
    1. query 带 child_id：整批导入到该孩子（须在 accessible 内）
    2. query 不带 child_id：CSV 必须包含 child_id 列（每行校验 accessible）
    """
    from config import settings
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "仅支持 CSV 文件")

    content = await file.read()
    max_bytes = int(settings.max_upload_size_mb) * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(413, f"文件超过 {settings.max_upload_size_mb}MB 限制（实际 {len(content)/1024/1024:.1f}MB）")
    content = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))

    required_headers = {"subject", "exam_name", "score", "exam_date"}
    if not required_headers.issubset(set(reader.fieldnames or [])):
        raise HTTPException(400, f"CSV 缺少必要列：{required_headers - set(reader.fieldnames or [])}")

    imported = 0
    errors = []
    for row_num, row in enumerate(reader, start=2):
        target_child_id = child_id or int(row.get("child_id", 0) or 0)
        if not target_child_id:
            errors.append(f"第 {row_num} 行：缺少 child_id")
            continue
        if target_child_id not in accessible:
            errors.append(f"第 {row_num} 行：child_id={target_child_id} 无权访问")
            continue
        try:
            child = await db.get(Child, target_child_id)
            if not child:
                errors.append(f"第 {row_num} 行：孩子档案 id={target_child_id} 不存在")
                continue

            exam_date_str = row.get("exam_date", "").strip()
            if not exam_date_str:
                errors.append(f"第 {row_num} 行：缺少 exam_date")
                continue

            def _float(v):
                try:
                    return float(v) if v != "" else None
                except ValueError:
                    return None

            def _int(v):
                try:
                    return int(v) if v != "" else None
                except ValueError:
                    return None

            payload = ExamCreate(
                child_id=target_child_id,
                subject=row.get("subject", "").strip(),
                exam_name=row.get("exam_name", "").strip(),
                exam_type=row.get("exam_type", "quiz").strip() or "quiz",
                score=float(row.get("score", 0)),
                full_score=_float(row.get("full_score")) or 100.0,
                class_rank=_int(row.get("class_rank")),
                grade_rank=_int(row.get("grade_rank")),
                exam_date=date.fromisoformat(exam_date_str),
                knowledge_points=[k.strip() for k in (row.get("knowledge_points") or "").split("|") if k.strip()],
                wrong_questions=row.get("wrong_questions") or None,
                teacher_comment=row.get("teacher_comment") or None,
                note=row.get("note") or None,
                grade_snapshot=row.get("grade_snapshot") or None,
                class_average=_float(row.get("class_average")),
            )
            exam = Exam(**payload.model_dump())
            db.add(exam)
            imported += 1
        except Exception as e:
            errors.append(f"第 {row_num} 行：{e!s}")

    await db.commit()

    msg = f"成功导入 {imported} 条考试记录"
    if errors:
        msg += f"，失败 {len(errors)} 条：" + "；".join(errors[:5])
    return OkResponse(message=msg)


@router.post("/homeworks", response_model=OkResponse)
async def import_homeworks(
    file: UploadFile = File(...),
    child_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """上传作业 CSV 批量导入"""
    from config import settings
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "仅支持 CSV 文件")

    content = await file.read()
    max_bytes = int(settings.max_upload_size_mb) * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(413, f"文件超过 {settings.max_upload_size_mb}MB 限制（实际 {len(content)/1024/1024:.1f}MB）")
    content = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))

    required_headers = {"subject", "title", "homework_date"}
    if not required_headers.issubset(set(reader.fieldnames or [])):
        raise HTTPException(400, f"CSV 缺少必要列：{required_headers - set(reader.fieldnames or [])}")

    imported = 0
    errors = []
    for row_num, row in enumerate(reader, start=2):
        target_child_id = child_id or int(row.get("child_id", 0) or 0)
        if not target_child_id:
            errors.append(f"第 {row_num} 行：缺少 child_id")
            continue
        if target_child_id not in accessible:
            errors.append(f"第 {row_num} 行：child_id={target_child_id} 无权访问")
            continue
        try:
            child = await db.get(Child, target_child_id)
            if not child:
                errors.append(f"第 {row_num} 行：孩子档案 id={target_child_id} 不存在")
                continue

            hw_date_str = row.get("homework_date", "").strip()
            if not hw_date_str:
                errors.append(f"第 {row_num} 行：缺少 homework_date")
                continue

            def _float(v):
                try:
                    return float(v) if v != "" else None
                except ValueError:
                    return None

            def _int(v):
                try:
                    return int(v) if v != "" else None
                except ValueError:
                    return None

            payload = HomeworkCreate(
                child_id=target_child_id,
                subject=row.get("subject", "").strip(),
                title=row.get("title", "").strip(),
                homework_date=date.fromisoformat(hw_date_str),
                duration_minutes=_int(row.get("duration_minutes")),
                total_questions=_int(row.get("total_questions")),
                correct_questions=_int(row.get("correct_questions")),
                accuracy=_float(row.get("accuracy")),
                completed=str(row.get("completed", "true")).lower() in ("true", "1", "yes"),
                difficulty=row.get("difficulty", "normal").strip() or "normal",
                note=row.get("note") or None,
                grade_snapshot=row.get("grade_snapshot") or None,
            )
            hw = Homework(**payload.model_dump())
            db.add(hw)
            imported += 1
        except Exception as e:
            errors.append(f"第 {row_num} 行：{e!s}")

    await db.commit()

    msg = f"成功导入 {imported} 条作业记录"
    if errors:
        msg += f"，失败 {len(errors)} 条：" + "；".join(errors[:5])
    return OkResponse(message=msg)
