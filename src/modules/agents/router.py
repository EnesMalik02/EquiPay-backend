from fastapi import APIRouter

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("/", summary="List all agents")
async def list_agents():
    """Tüm agent'ları listeler (örnek endpoint)."""
    return {
        "agents": [],
        "message": "Agent listesi başarıyla getirildi.",
    }
