"""Integration tests for LatheCAM Web REST API and Mesh Generation."""

from __future__ import annotations

import io
from fastapi.testclient import TestClient
import pytest

from lathecam_web.main import app

client = TestClient(app)


def test_health_check() -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_get_project_state() -> None:
    res = client.get("/api/project")
    assert res.status_code == 200
    data = res.json()
    assert "name" in data
    assert len(data["operations"]) == 6
    assert len(data["faces"]) > 0
    assert data["stock"]["od_mm"] == 40.0
    assert "gcode_text" in data
    assert "M30" in data["gcode_text"]


def test_load_demo() -> None:
    res = client.post("/api/project/load_demo")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Stepped Threaded Drive Shaft"
    assert len(data["operations"]) == 6


def test_recalculate_project() -> None:
    # First get state
    state = client.get("/api/project").json()
    ops = state["operations"]
    # Change DOC of roughing op
    ops[1]["doc_mm"] = 1.0

    req_payload = {
        "operations": ops,
        "is_diameter_mode": True,
        "post_dialect": "linuxcnc",
    }
    res = client.post("/api/project/recalculate", json=req_payload)
    assert res.status_code == 200
    updated = res.json()
    assert updated["operations"][1]["doc_mm"] == 1.0
    assert updated["verification"]["is_valid"] is True


def test_face_operation_assignment() -> None:
    state = client.get("/api/project").json()
    face = state["faces"][0]
    initial_op_count = len(state["operations"])

    res = client.post(
        "/api/project/face_operation",
        json={"face_id": face["face_id"], "op_type": "OD Roughing"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["operations"]) == initial_op_count + 1
    new_op = data["operations"][-1]
    assert new_op["geometry_scope"] == "face"
    assert new_op["assigned_face_id"] == face["face_id"]


def test_mesh_generation() -> None:
    res_part = client.get("/api/project/mesh/part?cutaway=true")
    assert res_part.status_code == 200
    mesh = res_part.json()
    assert len(mesh["vertices"]) > 0
    assert len(mesh["normals"]) == len(mesh["vertices"])
    assert len(mesh["indices"]) % 3 == 0

    res_stock = client.get("/api/project/mesh/stock")
    assert res_stock.status_code == 200
    stock_mesh = res_stock.json()
    assert len(stock_mesh["vertices"]) > 0


def test_simulation_waypoints() -> None:
    res = client.get("/api/simulation/waypoints")
    assert res.status_code == 200
    waypoints = res.json()
    assert len(waypoints) > 50
    assert any(w["mode"] == "G0" for w in waypoints)
    assert any(w["mode"] == "G1" for w in waypoints)
    assert all("x_dia" in w for w in waypoints)


def test_gcode_download() -> None:
    res = client.get("/api/project/gcode?dialect=fanuc")
    assert res.status_code == 200
    assert "attachment; filename=" in res.headers.get("content-disposition", "")
    assert "%" in res.text or "M30" in res.text


def test_tool_endpoints() -> None:
    res_shapes = client.get("/api/tools/iso_shapes")
    assert res_shapes.status_code == 200
    assert "C" in res_shapes.json()
    assert "D" in res_shapes.json()

    res_presets = client.get("/api/tools/presets")
    assert res_presets.status_code == 200
    assert len(res_presets.json()) > 0
