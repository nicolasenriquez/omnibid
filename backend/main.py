from fastapi import FastAPI
from backend.api.routers.health import router as health_router
from backend.api.routers.operations import router as operations_router
from backend.core.config import get_settings
from backend.observability.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title="ChileCompra Data Platform", version="0.1.0")
app.include_router(health_router)
app.include_router(operations_router)
