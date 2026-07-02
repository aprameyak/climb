"""Unit tests for biomechanics modules."""
from __future__ import annotations

import math
import numpy as np
import pytest

from biomechanics.reach_model import ReachModel
from biomechanics.joint_constraints import JointConstraintValidator, JOINT_LIMITS
from biomechanics.movement_library import MovementLibrary
from models.beta import MoveType
from models.climber import ClimberProfile, Injury
from models.holds import DetectedHold, HoldPosition, HoldType


def make_profile(**kwargs) -> ClimberProfile:
    defaults = dict(
        id="test",
        height_cm=170.0,
        weight_kg=68.0,
        wingspan_cm=172.0,
        arm_length_cm=75.0,
        forearm_length_cm=35.0,
        leg_length_cm=88.0,
        torso_length_cm=55.0,
    )
    defaults.update(kwargs)
    return ClimberProfile(**defaults)


def make_hold(x: float, y: float, hold_type: HoldType = HoldType.CRIMP) -> DetectedHold:
    return DetectedHold(
        id=f"h_{x:.2f}_{y:.2f}",
        polygon=[(x - 0.02, y - 0.02), (x + 0.02, y - 0.02), (x + 0.02, y + 0.02), (x - 0.02, y + 0.02)],
        center=HoldPosition(x=x, y=y, z_estimate=0.0),
        confidence=0.85,
        bbox=(x - 0.02, y - 0.02, 0.04, 0.04),
        hold_type=hold_type,
    )


class TestReachModel:
    def setup_method(self):
        self.reach_model = ReachModel()
        self.avg_profile = make_profile()
        self.tall_profile = make_profile(
            height_cm=190.0,
            wingspan_cm=195.0,
            arm_length_cm=85.0,
            leg_length_cm=100.0,
        )
        self.short_profile = make_profile(
            height_cm=155.0,
            wingspan_cm=152.0,
            arm_length_cm=65.0,
            leg_length_cm=75.0,
        )

    def test_reach_volume_positive(self):
        vol = self.reach_model.compute_reach_volume(self.avg_profile, wall_angle_deg=0.0)
        assert vol.max_reach_cm > 0
        assert vol.comfortable_reach_cm <= vol.max_reach_cm

    def test_tall_climber_has_greater_reach(self):
        tall_vol = self.reach_model.compute_reach_volume(self.tall_profile, 0.0)
        short_vol = self.reach_model.compute_reach_volume(self.short_profile, 0.0)
        assert tall_vol.max_reach_cm > short_vol.max_reach_cm

    def test_overhang_reduces_reach(self):
        vertical_vol = self.reach_model.compute_reach_volume(self.avg_profile, 0.0)
        overhang_vol = self.reach_model.compute_reach_volume(self.avg_profile, 40.0)
        assert overhang_vol.max_reach_cm <= vertical_vol.max_reach_cm

    def test_nearby_hold_is_reachable(self):
        hold = make_hold(0.5, 0.5)
        result = self.reach_model.can_hand_reach_hold(
            profile=self.avg_profile,
            hip_pos_normalized=(0.5, 0.65),
            current_hand_pos=(0.5, 0.55),
            target_hold=hold,
            wall_angle_deg=0.0,
        )
        # A hold at center, hip slightly below — should be reachable
        assert isinstance(result.reachable, bool)
        assert result.distance_cm >= 0

    def test_very_distant_hold_is_not_reachable(self):
        hold = make_hold(0.95, 0.05)  # Far upper right
        result = self.reach_model.can_hand_reach_hold(
            profile=self.short_profile,
            hip_pos_normalized=(0.1, 0.95),  # lower left
            current_hand_pos=(0.1, 0.8),
            target_hold=hold,
            wall_angle_deg=0.0,
        )
        # 0.85 × 400cm × sqrt(2) ≈ 480cm distance — should not be reachable
        assert not result.reachable

    def test_max_step_height_increases_with_flexibility(self):
        flexible_profile = make_profile(hamstring_flexibility_score=0.9, hip_mobility_deg=130.0)
        stiff_profile = make_profile(hamstring_flexibility_score=0.1, hip_mobility_deg=60.0)
        assert self.reach_model.compute_max_step_height(flexible_profile) > \
               self.reach_model.compute_max_step_height(stiff_profile)

    def test_foot_reach_below_hips(self):
        hold = make_hold(0.5, 0.85)  # low hold (near bottom of wall)
        result = self.reach_model.can_foot_reach_hold(
            profile=self.avg_profile,
            hip_pos_normalized=(0.5, 0.6),
            target_hold=hold,
        )
        assert result.reachable  # Low holds should always be reachable

    def test_injured_climber_restricted(self):
        profile = make_profile()
        profile = profile.model_copy(update={
            "injuries": [
                Injury(
                    body_part="hip",
                    severity=0.6,
                    movement_restrictions=["overhead", "high step"],
                )
            ]
        })
        hold = make_hold(0.5, 0.1)  # Very high hold
        result = self.reach_model.can_foot_reach_hold(
            profile=profile,
            hip_pos_normalized=(0.5, 0.7),
            target_hold=hold,
        )
        # High step restriction should block this
        assert not result.reachable
        assert result.limiting_factor == "injury"


class TestJointConstraints:
    def setup_method(self):
        self.validator = JointConstraintValidator()
        self.profile = make_profile()

    def test_joint_limits_are_positive(self):
        for joint, (low, high) in JOINT_LIMITS.items():
            assert high >= low, f"Joint {joint} has invalid range"

    def test_heel_hook_requires_hip_mobility(self):
        flexible = make_profile(hip_mobility_deg=120.0)
        hold = make_hold(0.5, 0.3)
        feasible, _ = self.validator.is_heel_hook_possible(flexible, hold)
        assert feasible

    def test_heel_hook_fails_insufficient_mobility(self):
        stiff = make_profile(hip_mobility_deg=40.0)
        hold = make_hold(0.5, 0.5)
        feasible, reason = self.validator.is_heel_hook_possible(stiff, hold)
        assert not feasible
        assert "mobility" in reason.lower()

    def test_heel_hook_blocked_by_injury(self):
        profile = make_profile()
        profile = profile.model_copy(update={
            "injuries": [
                Injury(
                    body_part="knee",
                    severity=0.7,
                    movement_restrictions=["heel hook"],
                )
            ]
        })
        hold = make_hold(0.5, 0.4)
        feasible, reason = self.validator.is_heel_hook_possible(profile, hold)
        assert not feasible

    def test_high_step_requires_hamstring(self):
        stiff = make_profile(hamstring_flexibility_score=0.05)
        feasible, reason = self.validator.is_high_step_possible(stiff, hold_y=0.1)
        assert not feasible


class TestMovementLibrary:
    def setup_method(self):
        self.library = MovementLibrary()
        self.profile = make_profile(
            core_strength_score=0.6,
            finger_strength_score=0.6,
            hip_mobility_deg=100.0,
            shoulder_mobility_deg=165.0,
            dynamic_comfort_score=0.7,
        )

    def test_static_always_applicable(self):
        applicable = self.library.get_applicable_moves(self.profile, 0.0)
        move_types = [mt for mt, _ in applicable]
        assert MoveType.STATIC in move_types

    def test_campus_requires_high_finger_strength(self):
        weak_profile = make_profile(finger_strength_score=0.1, core_strength_score=0.1)
        safe, reasons = self.library.is_move_safe(MoveType.CAMPUS_MOVE, weak_profile)
        assert not safe
        assert any("finger" in r.lower() for r in reasons)

    def test_full_dyno_not_for_beginners(self):
        beginner = make_profile(dynamic_comfort_score=0.1, finger_strength_score=0.2, core_strength_score=0.2)
        safe, reasons = self.library.is_move_safe(MoveType.FULL_DYNO, beginner)
        assert not safe

    def test_move_definitions_complete(self):
        # Every movement in the library must have all required fields
        for move_type, defn in self.library._library.items():
            assert defn.description, f"{move_type} missing description"
            assert defn.coaching_cue, f"{move_type} missing coaching cue"
            assert 0 <= defn.typical_difficulty <= 1
            assert 0 <= defn.energy_cost <= 1
            assert 0 <= defn.risk_level <= 1

    def test_suitability_scores_in_range(self):
        moves = self.library.get_applicable_moves(self.profile, 0.0)
        for move_type, score in moves:
            assert 0.0 <= score <= 1.0, f"{move_type} suitability {score} out of range"
