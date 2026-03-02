from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.database import lifespan
from src.modules.auth.router import router as auth_router
from src.modules.users.router import router as users_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="EquiPay API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")

@app.get("/", summary="Health check")
async def health_check():
    return {
        "status": "ok",
        "message": "EquiPay API is running.",
    }