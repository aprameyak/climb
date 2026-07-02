from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, computed_field, model_validator


class ExperienceLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    ELITE = "elite"


class ClimbingStyle(str, Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"
    BALANCED = "balanced"
    POWERFUL = "powerful"
    TECHNICAL = "technical"
    SLOPEY = "slopey"
    CRIMPY = "crimpy"
    COMPRESSION = "compression"


class HandDominance(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    AMBIDEXTROUS = "ambidextrous"


class Injury(BaseModel):
    body_part: str = Field(..., description="Affected body part (e.g. 'A2 pulley', 'shoulder')")
    severity: float = Field(
        ..., ge=0.0, le=1.0, description="Severity (0=minor, 0.5=moderate, 1.0=major/acute)"
    )
    movement_restrictions: list[str] = Field(
        default_factory=list,
        description="Movements to avoid (e.g. 'full crimp', 'heel hook')",
    )
    notes: str = Field(default="")


class ClimberProfile(BaseModel):
    """Full anthropometric and capability profile of a climber."""

    id: str
    name: str = Field(default="Climber")

    # Anthropometrics
    height_cm: float = Field(..., gt=100.0, lt=250.0, description="Height in cm")
    weight_kg: float = Field(..., gt=30.0, lt=200.0, description="Body weight in kg")
    wingspan_cm: float = Field(
        ..., gt=100.0, lt=260.0, description="Wingspan (fingertip to fingertip) in cm"
    )
    arm_length_cm: float = Field(
        ..., gt=40.0, lt=120.0, description="Arm length shoulder to fingertip in cm"
    )
    forearm_length_cm: float = Field(
        ..., gt=20.0, lt=60.0, description="Forearm length elbow to fingertip in cm"
    )
    leg_length_cm: float = Field(
        ..., gt=60.0, lt=140.0, description="Leg length hip to floor in cm"
    )
    torso_length_cm: float = Field(
        ..., gt=30.0, lt=80.0, description="Torso length shoulder to hip in cm"
    )

    # Mobility (degrees)
    shoulder_mobility_deg: float = Field(
        default=160.0, ge=0.0, le=180.0, description="Maximum shoulder flexion in degrees"
    )
    hip_mobility_deg: float = Field(
        default=90.0, ge=0.0, le=180.0, description="Hip flexion range in degrees"
    )
    ankle_dorsiflexion_deg: float = Field(
        default=15.0, ge=-10.0, le=40.0, description="Ankle dorsiflexion in degrees"
    )
    hamstring_flexibility_score: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Hamstring flexibility (0=tight, 1=very flexible)"
    )

    # Strength scores (0-1)
    core_strength_score: float = Field(default=0.5, ge=0.0, le=1.0)
    finger_strength_score: float = Field(default=0.5, ge=0.0, le=1.0)
    pinch_strength_score: float = Field(default=0.4, ge=0.0, le=1.0)
    crimp_strength_score: float = Field(default=0.5, ge=0.0, le=1.0)
    sloper_ability_score: float = Field(default=0.4, ge=0.0, le=1.0)
    dynamic_comfort_score: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Comfort and ability with dynamic moves"
    )

    # Style and preferences
    preferred_style: ClimbingStyle = Field(default=ClimbingStyle.BALANCED)
    experience_level: ExperienceLevel = Field(default=ExperienceLevel.INTERMEDIATE)
    indoor_grade_v: int = Field(
        default=5, ge=0, le=17, description="Current highest indoor V-grade redpoint"
    )

    # Injuries and limitations
    injuries: list[Injury] = Field(default_factory=list)
    hand_dominance: HandDominance = Field(default=HandDominance.RIGHT)
    foot_dominance: HandDominance = Field(default=HandDominance.RIGHT)
    fear_of_dynamic: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Fear/reluctance for dynamic moves (0=fearless, 1=refuses all dynos)",
    )

    @computed_field  # type: ignore[misc]
    @property
    def ape_index(self) -> float:
        """Ape index = wingspan - height. Positive = good for climbing."""
        return self.wingspan_cm - self.height_cm

    @computed_field  # type: ignore[misc]
    @property
    def max_comfortable_reach_cm(self) -> float:
        """Maximum comfortable vertical reach above head.
        Based on arm length + shoulder mobility factor.
        """
        shoulder_factor = self.shoulder_mobility_deg / 180.0
        # From standing: arm_length * sin(shoulder_flexion) + some core extension
        import math

        reach = self.arm_length_cm * math.sin(
            math.radians(min(self.shoulder_mobility_deg, 170))
        )
        # Add torso height when standing
        reach += self.torso_length_cm * 0.3  # slight lean
        return round(reach, 1)

    @model_validator(mode="after")
    def validate_proportions(self) -> ClimberProfile:
        # Soft warning: wingspan should be reasonably close to height
        ratio = self.wingspan_cm / self.height_cm
        if not (0.85 <= ratio <= 1.15):
            # Not an error, just unusual
            pass
        return self

    def has_restriction(self, movement: str) -> bool:
        """Check if any injury restricts the given movement type."""
        movement_lower = movement.lower()
        for injury in self.injuries:
            for restriction in injury.movement_restrictions:
                if restriction.lower() in movement_lower or movement_lower in restriction.lower():
                    return True
        return False

    @classmethod
    def default_profile(cls) -> ClimberProfile:
        """Average recreational climber profile."""
        return cls(
            id="default",
            name="Default Climber",
            height_cm=170.0,
            weight_kg=68.0,
            wingspan_cm=172.0,
            arm_length_cm=75.0,
            forearm_length_cm=35.0,
            leg_length_cm=88.0,
            torso_length_cm=55.0,
            shoulder_mobility_deg=160.0,
            hip_mobility_deg=95.0,
            ankle_dorsiflexion_deg=15.0,
            hamstring_flexibility_score=0.5,
            core_strength_score=0.55,
            finger_strength_score=0.5,
            pinch_strength_score=0.45,
            crimp_strength_score=0.5,
            sloper_ability_score=0.4,
            dynamic_comfort_score=0.5,
            preferred_style=ClimbingStyle.BALANCED,
            experience_level=ExperienceLevel.INTERMEDIATE,
            indoor_grade_v=5,
            injuries=[],
            hand_dominance=HandDominance.RIGHT,
            foot_dominance=HandDominance.RIGHT,
            fear_of_dynamic=0.25,
        )
