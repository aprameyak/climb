from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from models.climber import ClimberProfile
from models.holds import DetectedHold


@dataclass
class ReachableVolume:
    """Describes the volume of space reachable from a given body position."""

    max_reach_cm: float
    comfortable_reach_cm: float
    overhang_adjustment: float = 1.0
    direction_bias: dict[str, float] = field(
        default_factory=lambda: {"up": 1.0, "left": 0.9, "right": 0.9, "down": 0.7, "cross": 0.8}
    )


@dataclass
class ReachabilityResult:
    reachable: bool
    distance_cm: float
    limiting_factor: str  # "height", "span", "flexibility", "injury", "feasible"
    margin_cm: float  # positive = comfortable, negative = over limit


class ReachModel:
    """Models the reachable space for a given climber on a given wall."""

    WALL_HEIGHT_M = 4.0
    WALL_WIDTH_M = 3.0

    def compute_reach_volume(
        self, profile: ClimberProfile, wall_angle_deg: float
    ) -> ReachableVolume:
        """Compute the maximum reach volume for a climber.

        On steeper overhangs, the effective reach decreases because
        the climber's body hangs further from the wall, reducing leverage.
        """
        base_reach_cm = profile.arm_length_cm
        shoulder_factor = profile.shoulder_mobility_deg / 180.0
        max_reach = base_reach_cm * shoulder_factor
        comfortable_reach = max_reach * 0.85
        overhang_factor = max(0.6, 1.0 - (max(0, wall_angle_deg) / 10.0) * 0.05)

        direction_bias = {
            "up": 1.0,
            "left": 0.9 if profile.hand_dominance.value == "right" else 1.0,
            "right": 1.0 if profile.hand_dominance.value == "right" else 0.9,
            "down": 0.7,
            "cross": 0.8,
        }

        return ReachableVolume(
            max_reach_cm=round(max_reach * overhang_factor, 1),
            comfortable_reach_cm=round(comfortable_reach * overhang_factor, 1),
            overhang_adjustment=overhang_factor,
            direction_bias=direction_bias,
        )

    def can_hand_reach_hold(
        self,
        profile: ClimberProfile,
        hip_pos_normalized: tuple[float, float],
        current_hand_pos: tuple[float, float],
        target_hold: DetectedHold,
        wall_angle_deg: float,
        wall_height_m: float = 4.0,
        wall_width_m: float = 3.0,
    ) -> ReachabilityResult:
        """Determine if a hand can reach the target hold from the current body position.

        All positions are in normalized (0-1) wall coordinates.

        Args:
            profile: Climber anthropometrics.
            hip_pos_normalized: Current hip position (x, y) normalized.
            current_hand_pos: Current hand position (x, y) normalized.
            target_hold: Target hold to reach.
            wall_angle_deg: Wall angle in degrees from vertical.
            wall_height_m: Wall height for scale.
            wall_width_m: Wall width for scale.

        Returns:
            ReachabilityResult describing whether and how easily the hold can be reached.
        """
        reach_volume = self.compute_reach_volume(profile, wall_angle_deg)

        # In wall coords: y=0 is top, y=1 is bottom
        hip_x_cm = hip_pos_normalized[0] * wall_width_m * 100
        hip_y_cm = (1.0 - hip_pos_normalized[1]) * wall_height_m * 100

        shoulder_height_cm = hip_y_cm + profile.torso_length_cm * 0.7
        shoulder_x_cm = hip_x_cm

        target_x_cm = target_hold.center.x * wall_width_m * 100
        target_y_cm = (1.0 - target_hold.center.y) * wall_height_m * 100

        dx = target_x_cm - shoulder_x_cm
        dy = target_y_cm - shoulder_height_cm  # positive = above shoulder
        distance_cm = math.sqrt(dx**2 + dy**2)

        if profile.has_restriction("overhead") and dy > 20:
            return ReachabilityResult(
                reachable=False,
                distance_cm=distance_cm,
                limiting_factor="injury",
                margin_cm=-(distance_cm - reach_volume.comfortable_reach_cm),
            )

        direction = "up" if dy > 10 else ("down" if dy < -20 else ("left" if dx < 0 else "right"))
        direction_factor = reach_volume.direction_bias.get(direction, 0.9)
        effective_reach = reach_volume.max_reach_cm * direction_factor

        margin = effective_reach - distance_cm
        reachable = margin >= 0

        if not reachable:
            if distance_cm > profile.max_comfortable_reach_cm * 1.2:
                limiting_factor = "height"
            elif abs(dx) > profile.arm_length_cm * 0.9:
                limiting_factor = "span"
            else:
                limiting_factor = "height"
        else:
            limiting_factor = "feasible"

        return ReachabilityResult(
            reachable=reachable,
            distance_cm=round(distance_cm, 1),
            limiting_factor=limiting_factor,
            margin_cm=round(margin, 1),
        )

    def can_foot_reach_hold(
        self,
        profile: ClimberProfile,
        hip_pos_normalized: tuple[float, float],
        target_hold: DetectedHold,
        wall_height_m: float = 4.0,
        wall_width_m: float = 3.0,
    ) -> ReachabilityResult:
        """Determine if a foot can reach the target hold."""
        hip_y_cm = (1.0 - hip_pos_normalized[1]) * wall_height_m * 100
        hip_x_cm = hip_pos_normalized[0] * wall_width_m * 100

        target_x_cm = target_hold.center.x * wall_width_m * 100
        target_y_cm = (1.0 - target_hold.center.y) * wall_height_m * 100

        dx = target_x_cm - hip_x_cm
        dy = hip_y_cm - target_y_cm  # positive = below hips (normal)

        distance_cm = math.sqrt(dx**2 + dy**2)

        max_foot_reach = self.compute_max_step_height(profile)

        if dy >= 0:
            max_lateral = profile.leg_length_cm * 0.7
            if abs(dx) > max_lateral:
                return ReachabilityResult(
                    reachable=False,
                    distance_cm=distance_cm,
                    limiting_factor="span",
                    margin_cm=max_lateral - abs(dx),
                )
            return ReachabilityResult(
                reachable=True,
                distance_cm=distance_cm,
                limiting_factor="feasible",
                margin_cm=max_lateral - abs(dx),
            )
        else:
            above_hip_cm = abs(dy)
            if above_hip_cm > max_foot_reach:
                return ReachabilityResult(
                    reachable=False,
                    distance_cm=distance_cm,
                    limiting_factor="flexibility",
                    margin_cm=max_foot_reach - above_hip_cm,
                )
            if profile.has_restriction("high step"):
                return ReachabilityResult(
                    reachable=False,
                    distance_cm=distance_cm,
                    limiting_factor="injury",
                    margin_cm=-1.0,
                )
            return ReachabilityResult(
                reachable=True,
                distance_cm=distance_cm,
                limiting_factor="feasible",
                margin_cm=max_foot_reach - above_hip_cm,
            )

    def compute_max_step_height(self, profile: ClimberProfile) -> float:
        """Maximum height a foot can be placed above hip level (cm).

        Depends on hip flexibility and hamstring flexibility.
        """
        base_height = profile.leg_length_cm * 0.3  # conservative base
        flexibility_bonus = profile.hamstring_flexibility_score * profile.leg_length_cm * 0.4
        hip_bonus = (profile.hip_mobility_deg / 130.0) * profile.leg_length_cm * 0.2
        return base_height + flexibility_bonus + hip_bonus
