from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .holds import DetectedHold
from .routes import BoardType, ClimbingRoute, WallGeometry
from .beta import BetaSolution


class DifficultyAnalysis(BaseModel):
    """Estimated difficulty and intensity breakdown for a route."""

    grade_v_estimate: int = Field(
        ..., ge=0, le=17, description="Estimated V-scale grade"
    )
    grade_font_estimate: str = Field(
        ..., description="Estimated Fontainebleau grade (e.g. '6a', '7b+')"
    )
    crux_description: str = Field(
        ..., description="Description of the crux section and what makes it hard"
    )
    power_intensity: float = Field(
        ..., ge=0.0, le=1.0, description="How much raw pulling power is needed"
    )
    finger_intensity: float = Field(
        ..., ge=0.0, le=1.0, description="Finger strength demand"
    )
    core_intensity: float = Field(
        ..., ge=0.0, le=1.0, description="Core engagement required"
    )
    coordination_intensity: float = Field(
        ..., ge=0.0, le=1.0, description="Coordination and timing required"
    )
    balance_intensity: float = Field(
        ..., ge=0.0, le=1.0, description="Balance difficulty"
    )
    mobility_intensity: float = Field(
        ..., ge=0.0, le=1.0, description="Flexibility/mobility required"
    )
    risk_level: float = Field(
        ..., ge=0.0, le=1.0, description="Overall injury/fall risk"
    )
    flash_probability: float = Field(
        ..., ge=0.0, le=1.0, description="Average flash probability for a climber at this grade"
    )
    send_probability: float = Field(
        ..., ge=0.0, le=1.0, description="Average send probability with practice"
    )
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence in this difficulty assessment"
    )


class VisionPipelineResult(BaseModel):
    """Complete output from the computer vision pipeline."""

    image_path: str = Field(..., description="Path to the primary analyzed image")
    wall_detected: bool = Field(
        ..., description="Whether a climbing wall was detected in the image"
    )
    wall_geometry: Optional[WallGeometry] = Field(
        default=None, description="Detected wall geometry"
    )
    holds: list[DetectedHold] = Field(
        default_factory=list, description="All detected holds"
    )
    route_candidates: list[ClimbingRoute] = Field(
        default_factory=list,
        description="Candidate routes identified in the image",
    )
    active_route: Optional[ClimbingRoute] = Field(
        default=None, description="Most likely active route"
    )
    processing_time_ms: float = Field(
        ..., ge=0.0, description="Total processing time in milliseconds"
    )
    overall_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Overall pipeline confidence"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal warnings (poor image quality, multiple routes, etc.)",
    )
    requires_additional_images: bool = Field(
        default=False,
        description="Whether additional images would improve accuracy significantly",
    )
    confidence_breakdown: dict[str, float] = Field(
        default_factory=dict,
        description="Confidence breakdown by component (wall_detection, hold_count, etc.)",
    )
    image_quality: dict[str, float] = Field(
        default_factory=dict,
        description="Image quality metrics (blur_score, exposure_score, noise_score)",
    )


class AnalysisRequest(BaseModel):
    """Input request for route analysis."""

    image_paths: list[str] = Field(
        ..., min_length=1, description="Paths to uploaded images (relative to storage)"
    )
    climber_profile_id: Optional[str] = Field(
        default=None,
        description="ID of climber profile to use for personalized beta",
    )
    board_type: BoardType = Field(default=BoardType.UNKNOWN)
    notes: Optional[str] = Field(
        default=None,
        description="User-provided notes (e.g. 'V6 yellow tape route, right side of wall')",
    )
    beta_types_requested: list[str] = Field(
        default_factory=lambda: ["high_percentage", "energy_efficient"],
        description="Which beta types to generate",
    )


class AnalysisResult(BaseModel):
    """Complete output from a full route analysis."""

    id: str
    request: AnalysisRequest
    vision_result: VisionPipelineResult
    betas: list[BetaSolution] = Field(default_factory=list)
    difficulty: Optional[DifficultyAnalysis] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    climber_profile_id: Optional[str] = Field(default=None)

    @property
    def primary_beta(self) -> Optional[BetaSolution]:
        """Return the high-percentage beta if available, else first beta."""
        for b in self.betas:
            if b.beta_type.value == "high_percentage":
                return b
        return self.betas[0] if self.betas else None
