"""FastAPI Router for LatheCAM Web API."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile

from lathecam.cam.tools import ISO_INSERT_PRESETS, ISO_SHAPE_DESCRIPTIONS
from lathecam_web.schemas import (
    AddFaceOpRequest,
    ProjectStateSchema,
    RecalculateRequest,
    SimulationWaypoint,
)
from lathecam_web.service import web_service

router = APIRouter(prefix="/api")


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "app": "LatheCAM Web"}


@router.get("/project", response_model=ProjectStateSchema)
def get_project() -> ProjectStateSchema:
    return web_service.get_state()


@router.post("/project/load_demo", response_model=ProjectStateSchema)
def load_demo() -> ProjectStateSchema:
    return web_service.load_demo()


@router.post("/project/recalculate", response_model=ProjectStateSchema)
def recalculate(req: RecalculateRequest) -> ProjectStateSchema:
    return web_service.update_project(
        name=req.name,
        stock=req.stock,
        operations=req.operations,
        tools=req.tools,
        is_diameter_mode=req.is_diameter_mode,
        post_dialect=req.post_dialect,
    )


@router.post("/project/face_operation", response_model=ProjectStateSchema)
def add_face_operation(req: AddFaceOpRequest) -> ProjectStateSchema:
    try:
        return web_service.add_face_operation(req.face_id, req.op_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cad/upload", response_model=ProjectStateSchema)
async def upload_cad_file(file: UploadFile = File(...)) -> ProjectStateSchema:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    try:
        return web_service.import_cad_file(file.filename or "uploaded.step", content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process CAD file: {e}")


@router.get("/project/mesh/part")
def get_part_mesh(cutaway: bool = Query(default=True)) -> dict[str, Any]:
    return web_service.get_mesh_part(cutaway=cutaway)


@router.get("/project/mesh/stock")
def get_stock_mesh() -> dict[str, Any]:
    return web_service.get_mesh_stock()


@router.get("/simulation/waypoints", response_model=list[SimulationWaypoint])
def get_simulation_waypoints() -> list[SimulationWaypoint]:
    return web_service.get_simulation_waypoints()


@router.get("/project/gcode")
def download_gcode(dialect: str = Query(default="linuxcnc")) -> Response:
    web_service.project.post_dialect = dialect
    web_service.project.recalculate_all()
    gcode = web_service.project.gcode_text
    filename = f"{web_service.project.name.replace(' ', '_')}.ngc"

    return Response(
        content=gcode,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/tools/iso_shapes")
def get_iso_shapes() -> dict[str, str]:
    return ISO_SHAPE_DESCRIPTIONS


@router.get("/tools/presets")
def get_tool_presets() -> dict[str, dict[str, Any]]:
    clean: dict[str, dict[str, Any]] = {}
    for name, data in ISO_INSERT_PRESETS.items():
        item = dict(data)
        if "orientation" in item and hasattr(item["orientation"], "value"):
            item["orientation"] = item["orientation"].value
        clean[name] = item
    return clean
