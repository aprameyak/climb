from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from models.climber import ClimberProfile
from models.holds import DetectedHold, HoldType


# Anatomical joint range of motion limits in degrees.
# These are physiological maxima — actual comfortable ranges are lower.
# Source: clinical biomechanics literature
JOINT_LIMITS: dict[str, tuple[float, float]] = {
    "shoulder_flexion": (0.0, 180.0),        # forward raise
    "shoulder_extension": (0.0, 60.0),        # backward reach
    "shoulder_abduction": (0.0, 180.0),       # side raise
    "shoulder_rotation_internal": (0.0, 90.0),
    "shoulder_rotation_external": (0.0, 90.0),
    "elbow_flexion": (0.0, 145.0),
    "elbow_extension": (-10.0, 0.0),           # hyperextension (negative)
    "wrist_flexion": (0.0, 80.0),
    "wrist_extension": (0.0, 70.0),
    "hip_flexion": (0.0, 130.0),               # knee to chest
    "hip_hyperflexion": (0.0, 150.0),          # with knee bent
    "hip_extension": (0.0, 30.0),
    "hip_abduction": (0.0, 45.0),
    "hip_rotation": (-45.0, 45.0),
    "knee_flexion": (0.0, 135.0),
    "knee_extension": (0.0, 10.0),             # hyperextension
    "ankle_dorsiflexion": (-20.0, 30.0),       # negative = plantarflexion
    "ankle_plantarflexion": (0.0, 50.0),
    "spine_flexion": (0.0, 45.0),
    "spine_extension": (0.0, 25.0),
    "spine_rotation": (-45.0, 45.0),
    "spine_lateral": (-25.0, 25.0),
}

# Comfortable working ranges (80% of anatomical max — sustainable for climbing)
COMFORTABLE_LIMITS: dict[str, tuple[float, float]] = {
    k: (v[0] * 0.8, v[1] * 0.85) for k, v in JOINT_LIMITS.items()
}


@dataclass
class JointViolation:
    joint: str
    current_angle: float
    limit: float
    severity: float  # 0-1: how far over limit
    message: str


class JointConstraintValidator:
    """Validates body positions against anatomical joint constraints."""

    def __init__(self) -> None:
        self.limits = JOINT_LIMITS
        self.comfortable = COMFORTABLE_LIMITS

    def validate_shoulder_position(
        self,
        hand_pos: np.ndarray,
        shoulder_pos: np.ndarray,
        profile: ClimberProfile,
        strict: bool = False,
    ) -> tuple[bool, list[JointViolation]]:
        """Check if a hand position is within shoulder range of motion.

        Args:
            hand_pos: Hand position in wall-space (x, y, z).
            shoulder_pos: Shoulder position in wall-space.
            profile: Climber profile with mobility values.
            strict: If True, use comfortable limits; else anatomical limits.

        Returns:
            (is_valid, violations)
        """
        violations: list[JointViolation] = []

        delta = hand_pos - shoulder_pos
        # Vertical component: shoulder flexion
        if delta[1] < 0:  # hand above shoulder (in wall coordinates y increases down)
            flexion_angle = self._vector_angle_vertical(delta)
            max_flexion = profile.shoulder_mobility_deg
            limit = max_flexion if not strict else max_flexion * 0.85
            if flexion_angle > limit:
                violations.append(
                    JointViolation(
                        joint="shoulder_flexion",
                        current_angle=flexion_angle,
                        limit=limit,
                        severity=(flexion_angle - limit) / limit,
                        message=f"Shoulder flexion {flexion_angle:.0f}° exceeds profile limit of {limit:.0f}°",
                    )
                )

        return len(violations) == 0, violations

    def validate_hip_rotation(
        self,
        hip_pos: np.ndarray,
        left_foot: np.ndarray,
        right_foot: np.ndarray,
        profile: ClimberProfile,
    ) -> tuple[bool, list[JointViolation]]:
        """Check if foot positions require excessive hip rotation."""
        violations: list[JointViolation] = []

        # Estimate hip rotation from foot spread
        foot_delta = right_foot - left_foot
        lateral_spread = abs(foot_delta[0])  # x-axis spread in normalized coords
        # Approximate: large lateral spread requires more hip rotation
        # At wall width of ~3m, full spread = 100% lateral = ~45 deg hip rotation
        estimated_hip_rotation = lateral_spread * 100 * 0.4  # rough estimate

        max_hip_rotation = abs(JOINT_LIMITS["hip_rotation"][1])
        if estimated_hip_rotation > max_hip_rotation:
            violations.append(
                JointViolation(
                    joint="hip_rotation",
                    current_angle=estimated_hip_rotation,
                    limit=max_hip_rotation,
                    severity=(estimated_hip_rotation - max_hip_rotation) / max_hip_rotation,
                    message=f"Foot spread requires {estimated_hip_rotation:.0f}° hip rotation (max {max_hip_rotation:.0f}°)",
                )
            )

        return len(violations) == 0, violations

    def is_heel_hook_possible(
        self, profile: ClimberProfile, hold: DetectedHold
    ) -> tuple[bool, str]:
        """Check if a heel hook on the given hold is physically possible."""
        # Heel hooks require hip flexion + external rotation
        min_hip_mobility = 80.0
        if profile.hip_mobility_deg < min_hip_mobility:
            return (
                False,
                f"Hip mobility ({profile.hip_mobility_deg:.0f}°) insufficient for heel hook (need {min_hip_mobility:.0f}°)",
            )

        # Check for restrictions
        if profile.has_restriction("heel hook"):
            return False, "Heel hook restricted due to injury"

        # High heel hooks (hold above hip height) require more hamstring flexibility
        if hold.center.y < 0.4:  # hold is high on wall
            if profile.hamstring_flexibility_score < 0.5:
                return (
                    False,
                    "Hamstring flexibility insufficient for high heel hook",
                )

        return True, "Heel hook is feasible"

    def is_high_step_possible(
        self, profile: ClimberProfile, hold_y: float
    ) -> tuple[bool, str]:
        """Check if stepping onto a high hold is possible.

        hold_y is normalized 0-1 (lower number = higher on wall).
        """
        # High steps require hip flexion and ankle dorsiflexion
        if hold_y < 0.25:  # very high step (above hip level)
            if profile.hip_mobility_deg < 110.0:
                return False, "Hip mobility insufficient for high step"
            if profile.hamstring_flexibility_score < 0.6:
                return False, "Hamstring flexibility insufficient for high step"

        if profile.has_restriction("high step"):
            return False, "High step restricted due to injury"

        return True, "High step feasible"

    def is_drop_knee_possible(self, profile: ClimberProfile) -> tuple[bool, str]:
        """Check if drop knee technique is feasible."""
        if profile.has_restriction("drop knee"):
            return False, "Drop knee restricted due to injury"
        if profile.hip_mobility_deg < 70.0:
            return False, "Insufficient hip mobility for drop knee"
        return True, "Drop knee feasible"

    def is_toe_hook_possible(self, profile: ClimberProfile) -> tuple[bool, str]:
        """Check if toe hook is physically feasible."""
        if profile.has_restriction("toe hook"):
            return False, "Toe hook restricted due to injury"
        return True, "Toe hook feasible"

    def check_all_constraints(
        self,
        hand_positions: tuple[np.ndarray, np.ndarray],
        foot_positions: tuple[np.ndarray, np.ndarray],
        hip_pos: np.ndarray,
        profile: ClimberProfile,
    ) -> list[str]:
        """Run all constraint checks and return list of violation messages."""
        violations: list[str] = []

        # Simplified shoulder check: hands shouldn't be impossibly high above hips
        for i, hand in enumerate(hand_positions):
            label = "Left hand" if i == 0 else "Right hand"
            # In normalized coords, y decreases as we go up
            height_above_hip = hip_pos[1] - hand[1]  # positive = above hips
            # Max comfortable overhead reach in normalized coords (~40cm / 400cm wall)
            max_overhead = (profile.arm_length_cm * 0.9) / 400.0
            if height_above_hip > max_overhead:
                violations.append(
                    f"{label} appears out of reach (beyond comfortable shoulder flexion)"
                )

        # Check foot spread
        lf, rf = foot_positions
        _, hip_violations = self.validate_hip_rotation(hip_pos, lf, rf, profile)
        violations.extend(v.message for v in hip_violations)

        return violations

    def _vector_angle_vertical(self, delta: np.ndarray) -> float:
        """Compute angle between delta vector and downward vertical."""
        import math
        if np.linalg.norm(delta) < 1e-10:
            return 0.0
        # delta[1] negative means upward in wall coords
        # Angle from vertical (straight up)
        angle = math.degrees(math.atan2(abs(delta[0]), abs(delta[1])))
        return angle
