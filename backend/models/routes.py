from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .holds import DetectedHold


class WallAngle(str, Enum):
    SLAB_70 = "slab_70"
    SLAB_80 = "slab_80"
    VERTICAL = "vertical"
    OVERHANG_5 = "overhang_5"
    OVERHANG_10 = "overhang_10"
    OVERHANG_15 = "overhang_15"
    OVERHANG_20 = "overhang_20"
    OVERHANG_25 = "overhang_25"
    OVERHANG_30 = "overhang_30"
    OVERHANG_35 = "overhang_35"
    OVERHANG_40 = "overhang_40"
    OVERHANG_45 = "overhang_45"
    ROOF = "roof"


# Degrees from vertical (negative = slab, positive = overhang)
WALL_ANGLE_DEGREES: dict[WallAngle, float] = {
    WallAngle.SLAB_70: -20.0,
    WallAngle.SLAB_80: -10.0,
    WallAngle.VERTICAL: 0.0,
    WallAngle.OVERHANG_5: 5.0,
    WallAngle.OVERHANG_10: 10.0,
    WallAngle.OVERHANG_15: 15.0,
    WallAngle.OVERHANG_20: 20.0,
    WallAngle.OVERHANG_25: 25.0,
    WallAngle.OVERHANG_30: 30.0,
    WallAngle.OVERHANG_35: 35.0,
    WallAngle.OVERHANG_40: 40.0,
    WallAngle.OVERHANG_45: 45.0,
    WallAngle.ROOF: 90.0,
}


class BoardType(str, Enum):
    MOONBOARD = "moonboard"
    KILTER = "kilter"
    TENSION = "tension"
    SPRAY = "spray"
    GYM = "gym"
    UNKNOWN = "unknown"


class WallGeometry(BaseModel):
    """Physical geometry of the climbing wall."""

    angle_degrees: float = Field(
        ...,
        ge=-30.0,
        le=90.0,
        description="Degrees from vertical (negative=slab, 0=vertical, positive=overhang)",
    )
    wall_type: WallAngle = Field(default=WallAngle.VERTICAL)
    height_m: float = Field(default=4.0, gt=0.0, description="Estimated wall height in meters")
    width_m: float = Field(default=3.0, gt=0.0, description="Estimated wall width in meters")
    has_volumes: bool = Field(default=False)
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence in this geometry estimate"
    )


class EdgeType(str, Enum):
    HAND_TO_HAND = "hand_to_hand"
    FOOT_TO_FOOT = "foot_to_foot"
    HAND_TO_FOOT = "hand_to_foot"
    FOOT_TO_HAND = "foot_to_hand"


class RouteEdge(BaseModel):
    """A possible transition between two holds in the route graph."""

    from_hold_id: str
    to_hold_id: str
    edge_type: EdgeType = Field(default=EdgeType.HAND_TO_HAND)
    required_reach_cm: float = Field(
        ..., ge=0.0, description="Minimum reach required for this transition in cm"
    )
    required_hip_rotation_deg: float = Field(
        default=0.0, description="Hip rotation required in degrees"
    )
    required_shoulder_rotation_deg: float = Field(
        default=0.0, description="Shoulder rotation required in degrees"
    )
    required_knee_flexion_deg: float = Field(
        default=0.0, description="Knee flexion angle required"
    )
    body_position_hint: str = Field(
        default="",
        description="Suggested body position for this transition",
    )
    momentum_required: bool = Field(
        default=False, description="Whether dynamic momentum is needed"
    )
    estimated_difficulty: float = Field(
        default=5.0, ge=0.0, le=10.0, description="Estimated difficulty of this transition"
    )
    risk_level: float = Field(
        default=0.2, ge=0.0, le=1.0, description="Risk level of this transition"
    )
    energy_cost: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Relative energy cost (0=trivial, 1=maximal)"
    )
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence that this transition is possible"
    )


class RouteGraph(BaseModel):
    """Graph representation of a climbing route."""

    nodes: dict[str, DetectedHold] = Field(
        default_factory=dict, description="Map of hold_id -> DetectedHold"
    )
    edges: list[RouteEdge] = Field(
        default_factory=list, description="All possible transitions between holds"
    )

    def get_neighbors(self, hold_id: str) -> list[tuple[str, RouteEdge]]:
        """Return list of (neighbor_id, edge) pairs reachable from hold_id."""
        return [
            (edge.to_hold_id, edge)
            for edge in self.edges
            if edge.from_hold_id == hold_id
        ]

    def get_edges_between(
        self, from_id: str, to_id: str
    ) -> list[RouteEdge]:
        return [
            e
            for e in self.edges
            if e.from_hold_id == from_id and e.to_hold_id == to_id
        ]


class ClimbingRoute(BaseModel):
    """A complete climbing route with all metadata."""

    id: str
    name: str = Field(default="Unnamed Route")
    grade_v: Optional[int] = Field(
        default=None, ge=0, le=17, description="V-scale grade estimate"
    )
    grade_font: Optional[str] = Field(
        default=None, description="Fontainebleau grade estimate (e.g. '6a', '7b+')"
    )
    wall_geometry: WallGeometry
    holds: list[DetectedHold] = Field(default_factory=list)
    route_graph: Optional[RouteGraph] = Field(default=None)
    start_holds: list[str] = Field(
        default_factory=list, description="IDs of start holds"
    )
    finish_holds: list[str] = Field(
        default_factory=list, description="IDs of finish holds"
    )
    route_color: Optional[str] = Field(
        default=None, description="Tape/LED color identifying this route"
    )
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence in route identification"
    )
    board_type: BoardType = Field(default=BoardType.UNKNOWN)
    image_paths: list[str] = Field(
        default_factory=list, description="Paths to source images"
    )

    def get_hold(self, hold_id: str) -> Optional[DetectedHold]:
        """Look up a hold by ID."""
        for h in self.holds:
            if h.id == hold_id:
                return h
        return None
