from __future__ import annotations

from dataclasses import dataclass
import shapely.geometry


@dataclass
class Stock:
    """Represents a cylindrical stock workpiece for turning operations.
    
    Coordinates are defined in millimeters:
    - Z = 0.0 is the finished part front face.
    - Z > 0.0 represents facing stock allowance.
    - Z < 0.0 extends toward the lathe chuck.
    """
    od_mm: float
    z_end_mm: float
    z_start_mm: float = 0.0
    id_mm: float = 0.0

    def __post_init__(self) -> None:
        if self.od_mm <= 0:
            raise ValueError(f"Stock OD must be positive, got {self.od_mm}")
        if self.id_mm < 0:
            raise ValueError(f"Stock ID cannot be negative, got {self.id_mm}")
        if self.id_mm >= self.od_mm:
            raise ValueError(f"Stock ID ({self.id_mm}) must be strictly less than OD ({self.od_mm})")
        if self.z_start_mm <= self.z_end_mm:
            raise ValueError(f"Stock z_start ({self.z_start_mm}) must be greater than z_end ({self.z_end_mm})")

    @property
    def od_radius(self) -> float:
        return self.od_mm / 2.0

    @property
    def id_radius(self) -> float:
        return self.id_mm / 2.0

    @property
    def length(self) -> float:
        return abs(self.z_start_mm - self.z_end_mm)

    def to_shapely_box(self) -> shapely.geometry.Polygon:
        """Returns the 2D bounding cross-section box in (Z, X_radius) coordinate space."""
        # Box definition: box(minx, miny, maxx, maxy) -> box(min_z, min_x, max_z, max_x)
        return shapely.geometry.box(self.z_end_mm, self.id_radius, self.z_start_mm, self.od_radius)
