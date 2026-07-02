from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class HoldType(str, Enum):
    JUG = "jug"
    POSITIVE_EDGE = "positive_edge"
    INCUT = "incut"
    FLAT_EDGE = "flat_edge"
    CRIMP = "crimp"
    MICRO_CRIMP = "micro_crimp"
    POCKET = "pocket"
    MONO = "mono"
    POCKET_2F = "pocket_2f"
    POCKET_3F = "pocket_3f"
    SLOPER = "sloper"
    PINCH = "pinch"
    RAIL = "rail"
    HORN = "horn"
    SIDEPULL = "sidepull"
    UNDERCLING = "undercling"
    GASTON = "gaston"
    VOLUME = "volume"
    SCREW_ON = "screw_on"
    CHIP = "chip"
    FOOT_CHIP = "foot_chip"
    SMEAR = "smear"
    MACRO = "macro"
    DUAL_TEXTURE = "dual_texture"
    UNKNOWN = "unknown"


class GripDirection(str, Enum):
    PULL_DOWN = "pull_down"
    PULL_LEFT = "pull_left"
    PULL_RIGHT = "pull_right"
    UNDERCLING = "undercling"
    PINCH = "pinch"
    COMPRESS = "compress"
    SLAP = "slap"
    PALM = "palm"


class RouteMarkerType(str, Enum):
    START = "start"
    FINISH = "finish"
    INTERMEDIATE = "intermediate"
    NONE = "none"


class HoldPosition(BaseModel):
    """Normalized wall coordinates. (0,0) = top-left, (1,1) = bottom-right."""

    x: float = Field(..., ge=0.0, le=1.0, description="Normalized horizontal position")
    y: float = Field(..., ge=0.0, le=1.0, description="Normalized vertical position")
    z_estimate: float = Field(
        default=0.0,
        description="Estimated depth offset from wall surface in cm (positive = protruding)",
    )


class HoldPolygon(BaseModel):
    """Polygon describing hold boundary in normalized coordinates."""

    points: list[tuple[float, float]] = Field(
        ..., min_length=3, description="List of (x, y) normalized coordinate pairs"
    )

    @field_validator("points")
    @classmethod
    def validate_points(cls, v: list[tuple[float, float]]) -> list[tuple[float, float]]:
        for x, y in v:
            if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                raise ValueError(f"All polygon points must be normalized 0-1; got ({x}, {y})")
        return v


class SurfaceNormal(BaseModel):
    """Unit vector describing the surface normal of the hold."""

    dx: float = Field(..., description="X component of surface normal")
    dy: float = Field(..., description="Y component of surface normal")
    dz: float = Field(
        ...,
        description="Z component of surface normal (positive = facing climber)",
    )

    @model_validator(mode="after")
    def normalize(self) -> SurfaceNormal:
        import math

        magnitude = math.sqrt(self.dx**2 + self.dy**2 + self.dz**2)
        if magnitude < 1e-6:
            self.dz = 1.0
        else:
            self.dx /= magnitude
            self.dy /= magnitude
            self.dz /= magnitude
        return self


class HoldUsability(BaseModel):
    """Whether each limb can use this hold and estimated quality."""

    left_hand: bool = True
    right_hand: bool = True
    left_foot: bool = True
    right_foot: bool = True
    quality_lh: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Quality for left hand use (0=unusable, 1=ideal)"
    )
    quality_rh: float = Field(default=0.5, ge=0.0, le=1.0)
    quality_lf: float = Field(default=0.3, ge=0.0, le=1.0)
    quality_rf: float = Field(default=0.3, ge=0.0, le=1.0)


# Estimated depth by hold type (cm)
HOLD_TYPE_DEPTH_CM: dict[HoldType, float] = {
    HoldType.JUG: 5.0,
    HoldType.POSITIVE_EDGE: 2.5,
    HoldType.INCUT: 3.0,
    HoldType.FLAT_EDGE: 1.0,
    HoldType.CRIMP: 0.8,
    HoldType.MICRO_CRIMP: 0.4,
    HoldType.POCKET: 3.5,
    HoldType.MONO: 2.0,
    HoldType.POCKET_2F: 2.5,
    HoldType.POCKET_3F: 3.0,
    HoldType.SLOPER: 1.5,
    HoldType.PINCH: 4.0,
    HoldType.RAIL: 1.5,
    HoldType.HORN: 6.0,
    HoldType.SIDEPULL: 2.0,
    HoldType.UNDERCLING: 2.0,
    HoldType.GASTON: 2.0,
    HoldType.VOLUME: 15.0,
    HoldType.SCREW_ON: 1.5,
    HoldType.CHIP: 0.5,
    HoldType.FOOT_CHIP: 0.5,
    HoldType.SMEAR: 0.2,
    HoldType.MACRO: 8.0,
    HoldType.DUAL_TEXTURE: 2.0,
    HoldType.UNKNOWN: 2.0,
}

# Estimated friction by hold type (0-1)
HOLD_TYPE_FRICTION: dict[HoldType, float] = {
    HoldType.JUG: 0.85,
    HoldType.POSITIVE_EDGE: 0.75,
    HoldType.INCUT: 0.80,
    HoldType.FLAT_EDGE: 0.55,
    HoldType.CRIMP: 0.65,
    HoldType.MICRO_CRIMP: 0.55,
    HoldType.POCKET: 0.75,
    HoldType.MONO: 0.70,
    HoldType.POCKET_2F: 0.72,
    HoldType.POCKET_3F: 0.74,
    HoldType.SLOPER: 0.50,
    HoldType.PINCH: 0.70,
    HoldType.RAIL: 0.65,
    HoldType.HORN: 0.80,
    HoldType.SIDEPULL: 0.70,
    HoldType.UNDERCLING: 0.65,
    HoldType.GASTON: 0.65,
    HoldType.VOLUME: 0.60,
    HoldType.SCREW_ON: 0.70,
    HoldType.CHIP: 0.55,
    HoldType.FOOT_CHIP: 0.55,
    HoldType.SMEAR: 0.50,
    HoldType.MACRO: 0.65,
    HoldType.DUAL_TEXTURE: 0.70,
    HoldType.UNKNOWN: 0.60,
}


class DetectedHold(BaseModel):
    """A hold detected in the climbing wall image with full metadata."""

    id: str = Field(..., description="Unique identifier for this hold")
    polygon: list[tuple[float, float]] = Field(
        ..., description="Boundary polygon in normalized (0-1) coordinates"
    )
    center: HoldPosition = Field(..., description="Center point of the hold")
    orientation_degrees: float = Field(
        default=0.0,
        ge=0.0,
        lt=360.0,
        description="Hold orientation in degrees (0=up, 90=right, 180=down, 270=left)",
    )
    estimated_depth_cm: float = Field(
        default=2.0,
        ge=0.0,
        description="Estimated protrusion from wall surface in cm",
    )
    surface_normal: SurfaceNormal = Field(
        default_factory=lambda: SurfaceNormal(dx=0.0, dy=0.0, dz=1.0)
    )
    hold_type: HoldType = Field(default=HoldType.UNKNOWN)
    grip_direction: GripDirection = Field(default=GripDirection.PULL_DOWN)
    estimated_difficulty: float = Field(
        default=5.0,
        ge=0.0,
        le=17.0,
        description="Estimated V-scale difficulty contribution (0=V0, 17=V17)",
    )
    estimated_friction: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Friction coefficient estimate (0=frictionless, 1=maximum grip)",
    )
    usability: HoldUsability = Field(default_factory=HoldUsability)
    usable_hand_positions: list[HoldPosition] = Field(
        default_factory=list,
        description="Specific positions on the hold where a hand can grip",
    )
    usable_foot_positions: list[HoldPosition] = Field(
        default_factory=list,
        description="Specific positions on the hold where a foot can smear or edge",
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence that this is a real hold (0-1)"
    )
    bbox: tuple[float, float, float, float] = Field(
        ...,
        description="Bounding box (x, y, width, height) in normalized coordinates",
    )
    color_rgb: Optional[tuple[int, int, int]] = Field(
        default=None,
        description="Estimated hold color in RGB (0-255)",
    )
    is_start: bool = Field(default=False, description="Whether this is a start hold")
    is_finish: bool = Field(default=False, description="Whether this is a finish hold")
    route_id: Optional[str] = Field(
        default=None,
        description="Route this hold belongs to (by color or tape)",
    )
    marker_type: RouteMarkerType = Field(default=RouteMarkerType.NONE)

    @classmethod
    def with_type_defaults(cls, hold_type: HoldType, **kwargs) -> DetectedHold:
        """Create a hold with depth and friction defaults based on hold type."""
        kwargs.setdefault("estimated_depth_cm", HOLD_TYPE_DEPTH_CM[hold_type])
        kwargs.setdefault("estimated_friction", HOLD_TYPE_FRICTION[hold_type])
        return cls(hold_type=hold_type, **kwargs)
