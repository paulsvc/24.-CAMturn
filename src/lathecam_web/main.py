"""FastAPI Main Application Entrypoint for LatheCAM Web."""

from __future__ import annotations

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from lathecam_web.api import router

app = FastAPI(
    title="LatheCAM Web API",
    description="Cloud-native Web API and CAM Engine for CNC Turning",
    version="1.0.0",
)

# Enable CORS for local Vite dev server and remote hosts
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Mount frontend production build if available
# Check common static paths: Docker (/app/static), or local workspace (frontend/dist)
possible_static_paths = [
    Path("/app/static"),
    Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
]

static_dir: Path | None = None
for p in possible_static_paths:
    if p.is_dir() and (p / "index.html").is_file():
        static_dir = p
        break

if static_dir:
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = static_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_dir / "index.html")
else:
    @app.get("/")
    def index():
        return {
            "message": "LatheCAM Web API is active. Frontend build not detected. Explore /docs for OpenAPI specifications.",
            "endpoints": ["/api/health", "/api/project", "/docs"],
        }
