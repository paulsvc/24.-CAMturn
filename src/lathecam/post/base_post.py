from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Sequence

from lathecam.cam.commands import MotionCmd


class BasePostProcessor(ABC):
    """Abstract base class for CNC lathe post-processors."""

    def __init__(self, is_diameter_mode: bool = True) -> None:
        self.is_diameter_mode = is_diameter_mode

    @abstractmethod
    def export(
        self,
        commands: Sequence[MotionCmd],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Translates a list of standardized MotionCmd instances into dialect-specific G-code."""
        pass
