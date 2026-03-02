from fastapi import FastAPI
from src.core.database import lifespan
from src.modules.auth.router import router as auth_router
from src.modules.users.router import router as users_router

app = FastAPI(
    title="EquiPay API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(users_router)

@app.get("/", summary="Health check")
async def health_check():
    return {
        "status": "ok",
        "message": "EquiPay API is running.",
    }