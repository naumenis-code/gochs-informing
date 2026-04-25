from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": True,
        "redis": True,
        "asterisk": True,
        "pbx_registration": True
    }

@router.get("/channels/stats")
async def channel_stats():
    return {
        "total_channels": 50,
        "used_channels": 12,
        "free_channels": 38,
        "gochs_channels": 8,
        "inbound_calls": 3,
        "outbound_calls": 9
    }

@router.get("/inbound/recent")
async def recent_inbound(limit: int = 10):
    return {"calls": []}
