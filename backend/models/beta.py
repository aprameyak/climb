from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .holds import HoldPosition


class MoveType(str, Enum):
    STATIC = "static"
    DEADPOINT = "deadpoint"
    CONTROLLED_DYNO = "controlled_dyno"
    FULL_DYNO = "full_dyno"
    HAND_BUMP = "hand_bump"
    HAND_MATCH = "hand_match"
    FOOT_MATCH = "foot_match"
    DROP_KNEE = "drop_knee"
    BACKSTEP = "backstep"
    INSIDE_FLAG = "inside_flag"
    OUTSIDE_FLAG = "outside_flag"
    REVERSE_FLAG = "reverse_flag"
    HEEL_HOOK = "heel_hook"
    TOE_HOOK = "toe_hook"
    BICYCLE = "bicycle"
    SCUM = "scum"
    KNEEBAR = "kneebar"
    ROCK_OVER = "rock_over"
    HIGH_STEP = "high_step"
    MANTLE = "mantle"
    COMPRESSION = "compression"
    STEM = "stem"
    BRIDGE = "bridge"
    CROSS_THROUGH = "cross_through"
    CROSS_OVER = "cross_over"
    PALM_PRESS = "palm_press"
    CAMPUS_MOVE = "campus_move"
    CUT_LOOSE = "cut_loose"
    SWING_CONTROL = "swing_control"
    HIP_TWIST = "hip_twist"
    HIP_DRIVE = "hip_drive"
    SHOULDER_ROTATION = "shoulder_rotation"
    LOCKOFF = "lockoff"


class BetaType(str, Enum):
    SHORTEST = "shortest"
    TALL_CLIMBER = "tall_climber"
    STATIC = "static"
    DYNAMIC = "dynamic"
    COMPETITION = "competition"
    ENERGY_EFFICIENT = "energy_efficient"
    HIGH_PERCENTAGE = "high_percentage"
    LOW_POWER = "low_power"


class LimbPosition(BaseModel):
    """Position of a single limb (hand or foot)."""

    hold_id: Optional[str] = Field(
        default=None, description="ID of the hold being used (if on a hold)"
    )
    position: Optional[HoldPosition] = Field(
        default=None, description="Position on wall (used when no specific hold)"
    )
    is_on_wall: bool = Field(default=True, description="Whether limb is in contact with wall")
    flag_type: Optional[str] = Field(
        default=None,
        description="Flag description if limb is flagging (e.g. 'outside_flag', 'inside_flag')",
    )

    @property
    def is_flagging(self) -> bool:
        return self.flag_type is not None and not self.is_on_wall


class BodyPosition(BaseModel):
    """Complete body position description for a single moment in climbing."""

    left_hand: LimbPosition
    right_hand: LimbPosition
    left_foot: LimbPosition
    right_foot: LimbPosition
    hips_position: Optional[HoldPosition] = Field(
        default=None, description="Normalized hip position on wall"
    )
    torso_rotation_deg: float = Field(
        default=0.0,
        ge=-90.0,
        le=90.0,
        description="Torso rotation in degrees (positive=right side in, negative=left side in)",
    )
    head_direction: str = Field(
        default="up",
        description="Direction the climber's head is looking (up, next_hold, left, right)",
    )
    weight_distribution: dict[str, float] = Field(
        default_factory=lambda: {"lh": 0.25, "rh": 0.25, "lf": 0.25, "rf": 0.25},
        description="Weight distribution across limbs (should sum to ~1.0)",
    )
    center_of_mass: HoldPosition = Field(
        default_factory=lambda: HoldPosition(x=0.5, y=0.5, z_estimate=0.0)
    )


class ClimbingMove(BaseModel):
    """A single movement in a beta sequence."""

    move_number: int = Field(..., ge=1, description="Sequential move number (1-indexed)")
    description: str = Field(..., description="Plain-language description of this move")
    move_types: list[MoveType] = Field(
        ..., min_length=1, description="Movement techniques used in this move"
    )
    body_position: BodyPosition = Field(
        ..., description="Body position after completing this move"
    )
    difficulty_rating: float = Field(
        ..., ge=0.0, le=1.0, description="Relative difficulty of this move within the route"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="AI confidence that this move sequence is correct"
    )
    reasoning: str = Field(
        ..., description="Why this move is recommended (biomechanical reasoning)"
    )
    common_mistakes: list[str] = Field(
        default_factory=list,
        description="Common errors climbers make on this move",
    )
    alternative_options: list[str] = Field(
        default_factory=list,
        description="Alternative ways to execute this move",
    )
    energy_cost: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Relative energy expenditure for this move"
    )
    risk_level: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Fall/injury risk for this move"
    )
    physics_note: Optional[str] = Field(
        default=None,
        description="Relevant physics note (momentum, friction, balance)",
    )
    is_crux: bool = Field(
        default=False, description="Whether this is a crux (hardest) move of the route"
    )


class BetaSolution(BaseModel):
    """A complete beta solution for a climbing route."""

    id: str
    beta_type: BetaType
    climber_profile_id: str
    route_id: str
    moves: list[ClimbingMove] = Field(default_factory=list)
    total_energy_cost: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Cumulative energy cost (normalized)"
    )
    expected_flash_probability: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Probability of sending first try with this beta",
    )
    expected_send_probability: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Probability of eventually sending with this beta",
    )
    overall_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="AI confidence in this entire beta sequence",
        default=0.5,
    )
    crux_move_numbers: list[int] = Field(
        default_factory=list,
        description="Move numbers of the crux moves",
    )
    notes: str = Field(default="", description="General notes about this beta")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generation_warnings: list[str] = Field(
        default_factory=list,
        description="Warnings generated during beta computation",
    )

    @property
    def move_count(self) -> int:
        return len(self.moves)

    def get_crux_moves(self) -> list[ClimbingMove]:
        return [m for m in self.moves if m.is_crux]
