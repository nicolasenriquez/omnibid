import json
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.routers.health import router as health_router
from backend.api.routers.operations import router as operations_router
from backend.api.routers.opportunities import router as opportunities_router
from backend.core.config import get_settings
from backend.observability.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title="ChileCompra Data Platform", version="0.1.0")


class _CustomJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")


app.default_response_class = _CustomJSONResponse

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["Accept"],
)

app.include_router(health_router)
app.include_router(operations_router)
app.include_router(opportunities_router)
