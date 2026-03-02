from fastapi import FastAPI
from src.core.database import lifespan
from src.modules.agents.router import router as agents_router

app = FastAPI(
    title="EquiPay API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(agents_router)

@app.get("/", summary="Health check")
async def health_check():
    return {
        "status": "ok",
        "message": "EquiPay API is running.",
    }