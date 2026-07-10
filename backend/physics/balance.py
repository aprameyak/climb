from __future__ import annotations

import math

import numpy as np

from models.beta import MoveType


class BalanceAnalyzer:
    """Analyzes balance and center-of-mass stability for climbing positions."""

    def compute_com(
        self,
        hand_positions: tuple[np.ndarray, np.ndarray],
        foot_positions: tuple[np.ndarray, np.ndarray],
        hip_pos: np.ndarray,
        shoulder_pos: np.ndarray,
    ) -> np.ndarray:
        """Compute center of mass using simplified segment model.

        Based on Winter (2009) body segment parameters.
        All positions in normalized wall coordinates.
        """
        lh, rh = hand_positions
        lf, rf = foot_positions

        # Segment mass fractions (Winter 2009)
        hands_mass = 0.012  # 0.6% × 2
        forearms_mass = 0.032  # 1.6% × 2
        upper_arms_mass = 0.056  # 2.8% × 2
        trunk_mass = 0.497
        thighs_mass = 0.200  # 10% × 2
        shanks_mass = 0.093  # 4.65% × 2
        feet_mass = 0.029  # 1.45% × 2
        head_mass = 0.081

        # Simplified: approximate segment centers from landmarks
        hands_com = (lh + rh) / 2
        forearm_com = (hands_com + shoulder_pos) * 0.4 + shoulder_pos * 0.6
        trunk_com = (shoulder_pos + hip_pos) / 2
        legs_com = (hip_pos + (lf + rf) / 2) / 2
        feet_com = (lf + rf) / 2
        head_com = shoulder_pos + np.array([0, -0.05, 0])

        total_mass = (
            hands_mass + forearms_mass + upper_arms_mass
            + trunk_mass + thighs_mass + shanks_mass + feet_mass + head_mass
        )

        com = (
            hands_com * hands_mass
            + forearm_com * (forearms_mass + upper_arms_mass)
            + trunk_com * trunk_mass
            + legs_com * (thighs_mass + shanks_mass)
            + feet_com * feet_mass
            + head_com * head_mass
        ) / total_mass

        return com

    def is_balanced(
        self,
        com: np.ndarray,
        support_points: list[np.ndarray],
        wall_angle_deg: float,
    ) -> tuple[bool, float]:
        """Determine if COM projection falls within the support polygon.

        On vertical/overhang walls, the primary concern is preventing
        barn-door swing — the COM must be within the convex hull of
        contact points projected onto the wall plane.

        Args:
            com: Center of mass in normalized wall coordinates.
            support_points: List of contact point positions (hands and feet).
            wall_angle_deg: Wall angle (negative=slab, positive=overhang).

        Returns:
            (is_balanced, margin) where margin is how far COM is from instability (0-1).
        """
        active = [p for p in support_points if np.linalg.norm(p) > 0]
        if len(active) < 2:
            return False, 0.0

        xs = [p[0] for p in active]
        ys = [p[1] for p in active]
        com_x, com_y = com[0], com[1]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        # Buffer for shoe rubber contact
        buffer = 0.02

        in_x = (min_x - buffer) <= com_x <= (max_x + buffer)
        in_y = (min_y - buffer) <= com_y <= (max_y + buffer)

        if max_x > min_x:
            margin_x = min(com_x - (min_x - buffer), (max_x + buffer) - com_x) / (max_x - min_x + buffer)
        else:
            margin_x = buffer / buffer
        if max_y > min_y:
            margin_y = min(com_y - (min_y - buffer), (max_y + buffer) - com_y) / (max_y - min_y + buffer)
        else:
            margin_y = 0.5

        # On slab: Y stability matters more (gravitational)
        # On overhang: X stability matters more (barn door)
        if wall_angle_deg < 0:  # slab
            margin = margin_y * 0.7 + margin_x * 0.3
        else:
            margin = margin_x * 0.6 + margin_y * 0.4

        is_balanced = in_x and in_y
        return is_balanced, round(max(0.0, min(1.0, margin)), 3)

    def compute_barn_door_risk(
        self,
        contact_points: list[np.ndarray],
        com: np.ndarray,
        wall_angle_deg: float,
    ) -> float:
        """Estimate barn door risk (0=no risk, 1=certain barn door).

        Barn door occurs when:
        - Only one side has foot contact (asymmetric support)
        - COM is offset to the open side
        - Wall is steep (increases gravitational pull away from wall)
        """
        if len(contact_points) < 2:
            return 0.8  # Only one contact — high risk

        foot_xs = [p[0] for p in contact_points[-2:]]  # last two = feet
        foot_span = abs(foot_xs[0] - foot_xs[1]) if len(foot_xs) >= 2 else 0

        if foot_span < 0.05:  # feet close together
            asymmetry = 0.7
        else:
            foot_mid_x = sum(foot_xs) / len(foot_xs)
            lateral_offset = abs(com[0] - foot_mid_x)
            asymmetry = min(1.0, lateral_offset / (foot_span + 0.01))

        steepness_factor = max(0, wall_angle_deg) / 90.0
        risk = asymmetry * (0.3 + steepness_factor * 0.7)

        return round(min(1.0, max(0.0, risk)), 3)

    def estimate_swing(
        self,
        contact_points: list[np.ndarray],
        com: np.ndarray,
        wall_angle_deg: float,
        move_type: MoveType,
    ) -> float:
        """Estimate how much swing will occur during or after a move (0-1).

        High swing makes the next move harder and increases fall risk.
        """
        base_swing = 0.0

        if move_type in (MoveType.FULL_DYNO, MoveType.CONTROLLED_DYNO):
            base_swing = 0.7
        elif move_type == MoveType.DEADPOINT:
            base_swing = 0.3
        elif move_type == MoveType.CUT_LOOSE:
            base_swing = 0.8

        barn_door = self.compute_barn_door_risk(contact_points, com, wall_angle_deg)
        swing = base_swing * 0.4 + barn_door * 0.6

        return round(min(1.0, max(0.0, swing)), 3)
