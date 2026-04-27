"""routers/tags.py — §17 Tags & Labels."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
from database import DB, get_db
from models.misc import ProductTagsAssign, TagCreate

router = APIRouter()
_NOW = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731


@router.post("/tags", status_code=201)
async def create_tag(data: TagCreate, db: DB = Depends(get_db), _user: dict = Depends(get_current_user)):
    dup = await db.query("SELECT id FROM tag WHERE name = $name LIMIT 1", {"name": data.name})
    if dup:
        raise HTTPException(409, "Tag already exists")
    record = await db.create("tag", {**data.model_dump(), "created_at": _NOW()})
    return record


@router.get("/tags")
async def list_tags(db: DB = Depends(get_db)):
    return await db.query("SELECT * FROM tag ORDER BY name ASC")


@router.post("/products/{product_id}/tags", status_code=201)
async def assign_tags(
    product_id: str, data: ProductTagsAssign,
    db: DB = Depends(get_db), _user: dict = Depends(get_current_user),
):
    p = await db.select_one("product", product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    existing_tags = p.get("tags", [])
    merged = list(set(existing_tags + data.tags))
    await db.update("product", product_id, {"tags": merged, "updated_at": _NOW()})
    return {"tags": merged}


@router.delete("/products/{product_id}/tags/{tag}", status_code=204)
async def remove_tag(
    product_id: str, tag: str,
    db: DB = Depends(get_db), _user: dict = Depends(get_current_user),
):
    p = await db.select_one("product", product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    tags = [t for t in p.get("tags", []) if t != tag]
    await db.update("product", product_id, {"tags": tags, "updated_at": _NOW()})
