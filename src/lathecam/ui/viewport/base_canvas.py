from __future__ import annotations

from PySide6.QtWidgets import QWidget
from lathecam.models.project import LatheProject


class BaseViewportCanvas(QWidget):
    """Abstract base interface for LatheCAM 3D/2D rendering viewports."""

    def render_project(
        self,
        project: LatheProject,
        active_op_id: str | None = None,
    ) -> None:
        raise NotImplementedError
