from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.core.exceptions import AppError, app_error_handler, http_exception_handler, validation_error_handler
from src.core.lifespan import lifespan
from src.modules.auth.router import router as auth_router
from src.modules.users.router import router as users_router
from src.modules.groups.router import router as groups_router
from src.modules.expenses.router import router as expenses_router
from src.modules.settlements.router import router as settlements_router
from src.modules.notifications.router import router as notifications_router

app = FastAPI(
    title="EquiPay API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(groups_router, prefix="/api")
app.include_router(expenses_router, prefix="/api")
app.include_router(settlements_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")


@app.get("/", summary="Health check")
async def health_check():
    return {"status": "ok", "message": "EquiPay API is running."}
