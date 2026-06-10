"""FastAPI application for MirrorLens dashboard."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from mirrorlens_dashboard.routes import (
    config_router,
    investigate_router,
    snapshot_router,
    stream_router,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

_SEARCH_PATHS = [
    Path(os.environ.get("FRONTEND_DIST", "")) if os.environ.get("FRONTEND_DIST") else None,
    Path(__file__).resolve().parents[4] / "dashboard" / "frontend" / "dist",
    Path("/app/dashboard/frontend/dist"),
]
FRONTEND_DIST = next((p for p in _SEARCH_PATHS if p and p.is_dir()), Path("/nonexistent"))


def build_app() -> FastAPI:
    app = FastAPI(title="MirrorLens Dashboard API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(config_router, prefix="/api")
    app.include_router(snapshot_router, prefix="/api")
    app.include_router(stream_router, prefix="/api")
    app.include_router(investigate_router, prefix="/api")

    if FRONTEND_DIST.is_dir():
        assets_dir = FRONTEND_DIST / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str) -> FileResponse:
            file_path = FRONTEND_DIST / full_path
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(FRONTEND_DIST / "index.html")

    return app


app = build_app()
