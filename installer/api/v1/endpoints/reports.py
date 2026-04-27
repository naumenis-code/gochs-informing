from fastapi import APIRouter
router = APIRouter()
@router.get("/summary")
async def summary(): return {"campaigns": {"total": 0}, "calls": {"total": 0}}
