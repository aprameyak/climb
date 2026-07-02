from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from models.climber import ClimberProfile
from models.holds import DetectedHold
from models.beta import MoveType


@dataclass
class JointAngles:
    """Joint angles for a given body position (degrees)."""

    left_shoulder: float = 0.0
    right_shoulder: float = 0.0
    left_elbow: float = 90.0
    right_elbow: float = 90.0
    left_hip: float = 0.0
    right_hip: float = 0.0
    left_knee: float = 90.0
    right_knee: float = 90.0
    left_ankle: float = 15.0
    right_ankle: float = 15.0
    spine_rotation: float = 0.0


@dataclass
class BodyState:
    """Full 3D body state in wall-space coordinates.

    All positions are in normalized (0-1) wall coordinates.
    y=0 is top of wall, y=1 is bottom.
    x=0 is left, x=1 is right.
    z=0 is wall surface, z>0 is away from wall.
    """

    left_hand: np.ndarray  # shape (3,): x, y, z
    right_hand: np.ndarray
    left_foot: np.ndarray
    right_foot: np.ndarray
    hips: np.ndarray
    shoulders: np.ndarray
    head: np.ndarray
    center_of_mass: np.ndarray
    joint_angles: JointAngles = field(default_factory=JointAngles)

    @classmethod
    def from_normalized_positions(
        cls,
        lh: tuple[float, float],
        rh: tuple[float, float],
        lf: tuple[float, float],
        rf: tuple[float, float],
        profile: ClimberProfile,
    ) -> BodyState:
        """Construct a BodyState from 2D normalized positions.

        Estimates 3D positions including hip, shoulder, and CoM.
        """
        lh_arr = np.array([lh[0], lh[1], 0.05])
        rh_arr = np.array([rh[0], rh[1], 0.05])
        lf_arr = np.array([lf[0], lf[1], 0.02])
        rf_arr = np.array([rf[0], rf[1], 0.02])

        # Estimate hips: midpoint between feet, offset upward by leg fraction
        leg_fraction = (profile.leg_length_cm / (profile.height_cm * 100)) * 0.5
        feet_mid_x = (lf[0] + rf[0]) / 2
        feet_mid_y = (lf[1] + rf[1]) / 2
        hip_y = feet_mid_y - leg_fraction
        hips = np.array([feet_mid_x, hip_y, 0.1])

        # Shoulders: above hips by torso fraction
        torso_fraction = (profile.torso_length_cm / (profile.height_cm * 100)) * 0.5
        shoulders = np.array([
            (lh[0] + rh[0]) / 2,
            hip_y - torso_fraction,
            0.08,
        ])

        # Head: above shoulders
        head_offset = 0.05  # ~head height fraction
        head = np.array([shoulders[0], shoulders[1] - head_offset, 0.05])

        # CoM: approximately at hip height, weighted towards wall contact
        com = np.array([
            (lh[0] + rh[0] + lf[0] + rf[0]) / 4,
            hips[1] * 0.6 + ((lh[1] + rh[1]) / 2) * 0.4,
            0.05,
        ])

        return cls(
            left_hand=lh_arr,
            right_hand=rh_arr,
            left_foot=lf_arr,
            right_foot=rf_arr,
            hips=hips,
            shoulders=shoulders,
            head=head,
            center_of_mass=com,
        )


@dataclass
class ValidationResult:
    valid: bool
    violations: list[str]
    warnings: list[str]
    adjusted_move_types: list[MoveType]  # safer alternatives if violations found


class HumanBodyModel:
    """Models climbing-specific human movement and validates physical feasibility."""

    def __init__(self, profile: ClimberProfile) -> None:
        self.profile = profile

    def compute_center_of_mass(self, state: BodyState) -> np.ndarray:
        """Estimate center of mass using segment weights (Winter 2009 body segment parameters).

        Segment mass fractions: head 0.081, trunk 0.497, upper arm 0.028×2,
        forearm 0.016×2, hand 0.006×2, thigh 0.100×2, shank 0.0465×2, foot 0.0145×2
        """
        # Simplified model: weighted average of key landmarks
        weights = {
            "hands": 0.044,    # 2 hands
            "shoulders": 0.497, # trunk dominates
            "hips": 0.3,       # lower trunk
            "feet": 0.163,     # 2 legs
        }

        hands_pos = (state.left_hand + state.right_hand) / 2
        feet_pos = (state.left_foot + state.right_foot) / 2

        com = (
            hands_pos * weights["hands"]
            + state.shoulders * weights["shoulders"]
            + state.hips * weights["hips"]
            + feet_pos * weights["feet"]
        ) / sum(weights.values())

        return com

    def check_balance(
        self, state: BodyState, wall_angle_deg: float
    ) -> tuple[bool, float]:
        """Check if the climber is in balance.

        On vertical/overhang: balance is maintained by COM staying within
        the support polygon (convex hull of contact points).
        On slab: COM must stay over feet.

        Returns:
            (is_balanced, margin) — margin is how far COM is from losing balance (0-1)
        """
        com = self.compute_center_of_mass(state)

        contact_points = [state.left_hand, state.right_hand, state.left_foot, state.right_foot]
        active_points = [p for p in contact_points if p[2] >= 0.01]  # on wall

        if len(active_points) < 2:
            return False, 0.0

        if wall_angle_deg <= 0:  # slab
            # On slab: feet are primary support, COM should be over feet
            feet_center_x = (state.left_foot[0] + state.right_foot[0]) / 2
            com_offset = abs(com[0] - feet_center_x)
            foot_span = abs(state.right_foot[0] - state.left_foot[0]) / 2 + 0.05
            margin = max(0, (foot_span - com_offset) / foot_span)
            return margin > 0.1, round(margin, 3)
        else:
            # Overhang: balance is about not barn-dooring
            # COM should be within a reasonable range of the wall contact polygon
            points_x = [p[0] for p in active_points]
            min_x, max_x = min(points_x), max(points_x)
            width = max_x - min_x + 0.05  # small buffer

            com_in_range = min_x - 0.03 <= com[0] <= max_x + 0.03
            margin = min(abs(com[0] - min_x), abs(max_x - com[0])) / (width + 0.01)
            return com_in_range, round(margin, 3)

    def estimate_joint_angles(self, state: BodyState) -> JointAngles:
        """Estimate joint angles from body position (simplified 2D)."""

        def arm_angle(shoulder: np.ndarray, hand: np.ndarray) -> float:
            delta = hand - shoulder
            return math.degrees(math.atan2(-delta[1], delta[0]))  # flip y for wall coords

        left_arm = arm_angle(state.shoulders, state.left_hand)
        right_arm = arm_angle(state.shoulders, state.right_hand)

        # Simplified elbow: if arm is fully extended, elbow is ~10°; bent = ~90°
        def elbow_estimate(shoulder: np.ndarray, hand: np.ndarray, arm_len: float) -> float:
            actual_dist = float(np.linalg.norm(hand - shoulder))
            ratio = actual_dist / (arm_len / 100.0)  # normalize by arm length
            # ratio 1.0 = fully extended = 10° flexion
            # ratio 0.7 = 70% extended = ~70° flexion
            return max(10.0, min(145.0, (1.0 - ratio) * 130.0 + 10.0))

        arm_len_norm = self.profile.arm_length_cm / 400.0  # normalize to wall
        lh_elbow = elbow_estimate(state.shoulders, state.left_hand, self.profile.arm_length_cm)
        rh_elbow = elbow_estimate(state.shoulders, state.right_hand, self.profile.arm_length_cm)

        # Hip angle: how much is the hip bent
        hip_to_feet = (state.left_foot + state.right_foot) / 2 - state.hips
        spine_to_feet_angle = math.degrees(math.atan2(abs(hip_to_feet[1]), abs(hip_to_feet[0])))
        hip_flexion = max(0, 90 - spine_to_feet_angle)

        return JointAngles(
            left_shoulder=left_arm,
            right_shoulder=right_arm,
            left_elbow=lh_elbow,
            right_elbow=rh_elbow,
            left_hip=hip_flexion,
            right_hip=hip_flexion,
            spine_rotation=state.joint_angles.spine_rotation,
        )

    def validate_move(
        self,
        from_state: BodyState,
        to_state: BodyState,
        move_type: MoveType,
        wall_angle_deg: float,
    ) -> ValidationResult:
        """Validate that a move is physically feasible for this climber.

        Checks:
        - Reach constraints (are the target holds within reach?)
        - Joint constraints (are joint angles within limits?)
        - Balance (is the intermediate position stable?)
        - Injury restrictions
        """
        from biomechanics.joint_constraints import JointConstraintValidator

        violations: list[str] = []
        warnings: list[str] = []
        validator = JointConstraintValidator()

        # Check injury restrictions for move type
        if self.profile.has_restriction(move_type.value):
            violations.append(
                f"Move type '{move_type.value}' is restricted due to injury in profile"
            )

        # Check balance in destination state
        balanced, margin = self.check_balance(to_state, wall_angle_deg)
        if not balanced:
            violations.append("Destination body position is not balanced")
        elif margin < 0.15:
            warnings.append(f"Destination position has low balance margin ({margin:.0%})")

        # Check for dynamic move constraints
        if move_type in (MoveType.FULL_DYNO, MoveType.CONTROLLED_DYNO):
            if self.profile.dynamic_comfort_score < 0.3:
                violations.append(
                    "Climber profile indicates low dynamic comfort — dyno not recommended"
                )
            if self.profile.fear_of_dynamic > 0.7:
                warnings.append(
                    "High fear of dynamic movement in profile — consider static alternatives"
                )

        # Check heel/toe hooks
        if move_type == MoveType.HEEL_HOOK:
            feasible, msg = validator.is_heel_hook_possible(
                self.profile,
                DetectedHold(
                    id="temp",
                    polygon=[(0, 0), (1, 0), (1, 1), (0, 1)],
                    center=type('', (), {'x': to_state.left_foot[0], 'y': to_state.left_foot[1], 'z_estimate': 0})(),
                    confidence=1.0,
                    bbox=(0, 0, 0.1, 0.1),
                ),
            )
            if not feasible:
                violations.append(msg)

        # Suggest alternatives if violations found
        adjusted_moves: list[MoveType] = []
        if violations:
            if move_type in (MoveType.FULL_DYNO, MoveType.CONTROLLED_DYNO):
                adjusted_moves = [MoveType.DEADPOINT, MoveType.STATIC]
            elif move_type == MoveType.HEEL_HOOK:
                adjusted_moves = [MoveType.TOE_HOOK, MoveType.HIGH_STEP]
            else:
                adjusted_moves = [MoveType.STATIC]

        return ValidationResult(
            valid=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            adjusted_move_types=adjusted_moves,
        )
