from __future__ import annotations

import math

import numpy as np

from biomechanics.body_model import BodyState
from biomechanics.movement_library import MovementLibrary
from biomechanics.reach_model import ReachModel
from models.beta import BodyPosition, LimbPosition, MoveType
from models.climber import ClimberProfile
from models.holds import DetectedHold, HoldPosition
from models.routes import WallGeometry


class MoveGenerator:
    """Generates movement types and body positions for transitions between holds."""

    def __init__(self) -> None:
        self.movement_library = MovementLibrary()
        self.reach_model = ReachModel()

    def select_move_types(
        self,
        from_hold: DetectedHold | None,
        to_hold: DetectedHold,
        profile: ClimberProfile,
        wall_geometry: WallGeometry,
        hip_pos: tuple[float, float] = (0.5, 0.6),
    ) -> list[MoveType]:
        """Return ordered list of applicable move types (most to least recommended).

        Args:
            from_hold: Current hold being left (None if starting).
            to_hold: Target hold.
            profile: Climber profile.
            wall_geometry: Wall geometry.
            hip_pos: Current hip position in normalized coords.

        Returns:
            Ordered list of MoveType recommendations.
        """
        all_moves = self.movement_library.get_applicable_moves(profile, wall_geometry.angle_degrees)

        # Filter by what makes sense for this specific transition
        relevant = []
        for move_type, suitability in all_moves:
            if self._is_move_applicable(move_type, from_hold, to_hold, profile, wall_geometry, hip_pos):
                relevant.append((move_type, suitability))

        # Always have at least static as an option
        move_types = [m for m, _ in relevant]
        if MoveType.STATIC not in move_types:
            move_types.append(MoveType.STATIC)

        return move_types[:5]  # Return top 5

    def _is_move_applicable(
        self,
        move_type: MoveType,
        from_hold: DetectedHold | None,
        to_hold: DetectedHold,
        profile: ClimberProfile,
        wall_geometry: WallGeometry,
        hip_pos: tuple[float, float],
    ) -> bool:
        """Check if a move type makes sense for this specific transition."""
        # Always applicable
        if move_type == MoveType.STATIC:
            return True

        if move_type == MoveType.HEEL_HOOK:
            feasible, _ = self.movement_library.get(move_type) and (True, "")
            # Check if the hold is in a position where heel hooking makes sense
            return to_hold.center.y < hip_pos[1]  # hold is above hips

        if move_type == MoveType.HIGH_STEP:
            return to_hold.center.y < hip_pos[1] + 0.1  # fairly high hold

        if move_type == MoveType.DROP_KNEE:
            return wall_geometry.angle_degrees > 5  # more useful on overhang

        if move_type in (MoveType.FULL_DYNO, MoveType.CONTROLLED_DYNO):
            if from_hold is None:
                return False
            dx = abs(to_hold.center.x - from_hold.center.x)
            dy = from_hold.center.y - to_hold.center.y
            distance = math.sqrt(dx**2 + dy**2)
            reach_vol = self.reach_model.compute_reach_volume(profile, wall_geometry.angle_degrees)
            # Dyno is appropriate when hold is far
            return distance * 400 > reach_vol.comfortable_reach_cm

        if move_type == MoveType.DEADPOINT:
            if from_hold is None:
                return False
            reach_vol = self.reach_model.compute_reach_volume(profile, wall_geometry.angle_degrees)
            dx = to_hold.center.x - (from_hold.center.x if from_hold else 0.5)
            dy = to_hold.center.y - (from_hold.center.y if from_hold else 0.5)
            dist_cm = math.sqrt(dx**2 + dy**2) * 400
            return dist_cm > reach_vol.comfortable_reach_cm * 0.85

        if move_type == MoveType.COMPRESSION:
            # Compression requires two holds on opposing sides
            return wall_geometry.angle_degrees > 10  # more relevant on steep terrain

        if move_type == MoveType.KNEEBAR:
            from models.holds import HoldType
            return to_hold.hold_type == HoldType.VOLUME  # kneebars go on volumes

        if move_type in (MoveType.INSIDE_FLAG, MoveType.OUTSIDE_FLAG, MoveType.REVERSE_FLAG):
            # Flags make sense for balance compensation
            return True  # always potentially useful

        if move_type == MoveType.LOCKOFF:
            if from_hold is None:
                return False
            dy = from_hold.center.y - to_hold.center.y  # positive = up
            return dy > 0.1  # long reach upward benefits from lockoff

        if move_type == MoveType.BACKSTEP:
            dx = abs(to_hold.center.x - (from_hold.center.x if from_hold else 0.5))
            return dx > 0.1

        return True  # default: applicable

    def estimate_move_difficulty(
        self,
        move_type: MoveType,
        from_hold: DetectedHold | None,
        to_hold: DetectedHold,
        profile: ClimberProfile,
        wall_geometry: WallGeometry,
    ) -> float:
        """Estimate difficulty of a specific move (0-1)."""
        defn = self.movement_library.get(move_type)
        base_difficulty = defn.typical_difficulty if defn else 0.5

        # Adjust for hold quality
        hold_difficulty = to_hold.estimated_difficulty / 17.0
        wall_difficulty = max(0, wall_geometry.angle_degrees) / 90.0 * 0.3

        # Adjust for climber's grade relative to hold
        grade_diff = (to_hold.estimated_difficulty - profile.indoor_grade_v) / 17.0
        grade_penalty = max(0, grade_diff) * 0.3

        combined = (base_difficulty * 0.4 + hold_difficulty * 0.3 + wall_difficulty * 0.2 + grade_penalty * 0.1)
        return round(min(1.0, max(0.0, combined)), 3)

    def estimate_move_confidence(
        self,
        move_type: MoveType,
        from_hold: DetectedHold | None,
        to_hold: DetectedHold,
        profile: ClimberProfile,
    ) -> float:
        """Estimate AI confidence that this move recommendation is correct (0-1)."""
        conf = 0.7

        defn = self.movement_library.get(move_type)
        if defn is None:
            return 0.3

        # Lower confidence if move is near climber's limits
        if profile.finger_strength_score < defn.min_finger_strength + 0.1:
            conf -= 0.15

        if profile.core_strength_score < defn.min_core_strength + 0.1:
            conf -= 0.1

        # Higher confidence for simpler moves
        if move_type == MoveType.STATIC:
            conf += 0.1

        # Incorporate hold detection confidence
        conf *= to_hold.confidence

        return round(min(0.95, max(0.1, conf)), 3)

    def generate_body_position_hint(
        self,
        move_type: MoveType,
        lh_hold: DetectedHold | None,
        rh_hold: DetectedHold | None,
        lf_hold: DetectedHold | None,
        rf_hold: DetectedHold | None,
        profile: ClimberProfile,
        wall_geometry: WallGeometry,
    ) -> BodyPosition:
        """Generate a BodyPosition description for a given move."""

        def hold_to_limb(hold: DetectedHold | None) -> LimbPosition:
            if hold is None:
                return LimbPosition(hold_id=None, position=None, is_on_wall=False)
            return LimbPosition(
                hold_id=hold.id,
                position=hold.center,
                is_on_wall=True,
                flag_type=None,
            )

        lh = hold_to_limb(lh_hold)
        rh = hold_to_limb(rh_hold)
        lf = hold_to_limb(lf_hold)
        rf = hold_to_limb(rf_hold)

        # Flags
        if move_type == MoveType.INSIDE_FLAG:
            rh.flag_type = "inside_flag"
            rh.is_on_wall = False
        elif move_type == MoveType.OUTSIDE_FLAG:
            rh.flag_type = "outside_flag"
            rh.is_on_wall = False

        # Torso rotation
        torso_rotation = 0.0
        if move_type in (MoveType.DROP_KNEE, MoveType.BACKSTEP):
            torso_rotation = 25.0
        elif move_type == MoveType.COMPRESSION:
            torso_rotation = 0.0

        # Weight distribution
        weight_dist = {"lh": 0.3, "rh": 0.3, "lf": 0.2, "rf": 0.2}
        if move_type == MoveType.HEEL_HOOK:
            weight_dist = {"lh": 0.2, "rh": 0.2, "lf": 0.4, "rf": 0.2}
        elif move_type == MoveType.HIGH_STEP:
            weight_dist = {"lh": 0.15, "rh": 0.15, "lf": 0.5, "rf": 0.2}

        # COM estimate from positions
        active = [h for h in [lh_hold, rh_hold, lf_hold, rf_hold] if h is not None]
        if active:
            com_x = sum(h.center.x for h in active) / len(active)
            com_y = sum(h.center.y for h in active) / len(active)
        else:
            com_x, com_y = 0.5, 0.6

        return BodyPosition(
            left_hand=lh,
            right_hand=rh,
            left_foot=lf,
            right_foot=rf,
            hips_position=HoldPosition(x=com_x, y=min(1.0, com_y + 0.05), z_estimate=0.0),
            torso_rotation_deg=torso_rotation,
            head_direction="next_hold",
            weight_distribution=weight_dist,
            center_of_mass=HoldPosition(x=com_x, y=com_y, z_estimate=0.0),
        )
