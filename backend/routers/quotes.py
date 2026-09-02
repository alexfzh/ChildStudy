"""诗词 / 名言随机接口（孩子看板欢迎栏）"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import get_current_user
from models import Quote, User

router = APIRouter(prefix="/api/quotes", tags=["诗词名言"])


class QuoteOut(BaseModel):
    id: int
    content: str
    author: str
    source: str | None = None
    category: str

    model_config = ConfigDict(from_attributes=True)


@router.get("/random", response_model=QuoteOut)
async def get_random_quote(
    category: str | None = Query(default=None, pattern="^(poem|quote)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """随机返回一条诗词或名言（家长/孩子账号均可）"""
    stmt = select(Quote)
    if category:
        stmt = stmt.where(Quote.category == category)
    # SQLite: ORDER BY RANDOM() 随机取一条
    stmt = stmt.order_by(func.random()).limit(1)
    result = await db.execute(stmt)
    quote = result.scalars().first()
    if quote is None:
        # 表为空时兜底，避免前端报错
        quote = Quote(
            id=0,
            content="少年辛苦终身事，莫向光阴惰寸功。",
            author="唐·杜荀鹤",
            source="《题弟侄书堂》",
            category="poem",
        )
    return quote
