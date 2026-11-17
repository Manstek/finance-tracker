"""Точка входа FastAPI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.categories import router as categories_router
from app.api.operations import router as operations_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

# Единый формат ошибок {"detail": "понятное сообщение"} (FR-12)
register_error_handlers(app)

# Фронтенд (задача #7) работает с localhost:5500 и ходит в API напрямую из браузера
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = "/api/v1"
app.include_router(auth_router, prefix=api_prefix)
app.include_router(categories_router, prefix=api_prefix)
app.include_router(operations_router, prefix=api_prefix)
app.include_router(admin_router, prefix=api_prefix)


@app.get("/health")
def health() -> dict[str, str]:
    """Проверка живости сервиса."""
    return {"status": "ok"}
