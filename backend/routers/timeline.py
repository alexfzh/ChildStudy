"""成长时间轴路由"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import assert_child_access, child_id_filter, get_accessible_child_ids
from models import Child, Timeline
from schemas import OkResponse, TimelineCreate, TimelineOut, TimelineUpdate

router = APIRouter(prefix="/api/timeline", tags=["成长时间轴"])


@router.get("", response_model=List[TimelineOut])
async def list_events(
    child_id: Optional[int] = None,
    event_type: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    if child_id is not None:
        assert_child_access(accessible, child_id)
    stmt = select(Timeline).order_by(Timeline.event_date.desc(), Timeline.id.desc())
    stmt = stmt.where(child_id_filter(accessible, child_id, Timeline.child_id))
    if event_type:
        stmt = stmt.where(Timeline.event_type == event_type)
    if keyword:
        stmt = stmt.where(
            (Timeline.title.ilike(f"%{keyword}%"))
            | (Timeline.description.ilike(f"%{keyword}%"))
            | (Timeline.tags.as_json().ilike(f"%{keyword}%"))
        )
    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=TimelineOut, status_code=201)
async def create_event(
    payload: TimelineCreate,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    assert_child_access(accessible, payload.child_id)
    child = await db.get(Child, payload.child_id)
    if not child:
        raise HTTPException(404, "孩子档案不存在")
    ev = Timeline(**payload.model_dump())
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    return ev


@router.put("/{event_id}", response_model=TimelineOut)
async def update_event(
    event_id: int,
    payload: TimelineUpdate,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    ev = await db.get(Timeline, event_id)
    if not ev:
        raise HTTPException(404, "事件不存在")
    assert_child_access(accessible, ev.child_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(ev, k, v)
    await db.commit()
    await db.refresh(ev)
    return ev


@router.delete("/{event_id}", response_model=OkResponse)
async def delete_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    ev = await db.get(Timeline, event_id)
    if not ev:
        raise HTTPException(404, "事件不存在")
    assert_child_access(accessible, ev.child_id)
    await db.delete(ev)
    await db.commit()
    return OkResponse(message="已删除事件")
