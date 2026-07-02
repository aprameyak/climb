"""Unit tests for Pydantic models."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from models.holds import (
    DetectedHold,
    GripDirection,
    HoldPosition,
    HoldType,
    HoldUsability,
    SurfaceNormal,
    HOLD_TYPE_DEPTH_CM,
    HOLD_TYPE_FRICTION,
)
from models.routes import BoardType, ClimbingRoute, WallAngle, WallGeometry
from models.climber import ClimberProfile, ExperienceLevel, ClimbingStyle
from models.beta import BetaSolution, BetaType, BodyPosition, ClimbingMove, LimbPosition, MoveType


# ---- Hold models ----

def make_test_hold(**kwargs) -> DetectedHold:
    defaults = {
        "id": "h1",
        "polygon": [(0.4, 0.3), (0.5, 0.3), (0.5, 0.4), (0.4, 0.4)],
        "center": HoldPosition(x=0.45, y=0.35, z_estimate=0.0),
        "confidence": 0.85,
        "bbox": (0.4, 0.3, 0.1, 0.1),
    }
    defaults.update(kwargs)
    return DetectedHold(**defaults)


class TestDetectedHold:
    def test_basic_creation(self):
        hold = make_test_hold()
        assert hold.id == "h1"
        assert hold.hold_type == HoldType.UNKNOWN
        assert hold.confidence == 0.85

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            make_test_hold(confidence=1.5)
        with pytest.raises(ValidationError):
            make_test_hold(confidence=-0.1)

    def test_center_normalization(self):
        with pytest.raises(ValidationError):
            HoldPosition(x=1.5, y=0.5, z_estimate=0.0)

    def test_with_type_defaults(self):
        hold = DetectedHold.with_type_defaults(
            HoldType.JUG,
            id="test",
            polygon=[(0, 0), (0.1, 0), (0.1, 0.1), (0, 0.1)],
            center=HoldPosition(x=0.05, y=0.05, z_estimate=0.0),
            confidence=0.9,
            bbox=(0, 0, 0.1, 0.1),
        )
        assert hold.estimated_depth_cm == HOLD_TYPE_DEPTH_CM[HoldType.JUG]
        assert hold.estimated_friction == HOLD_TYPE_FRICTION[HoldType.JUG]

    def test_hold_type_enum_values(self):
        assert HoldType.CRIMP.value == "crimp"
        assert HoldType.MICRO_CRIMP.value == "micro_crimp"
        assert HoldType.POCKET_2F.value == "pocket_2f"

    def test_start_finish_markers(self):
        start_hold = make_test_hold(is_start=True, is_finish=False)
        assert start_hold.is_start is True
        assert start_hold.is_finish is False


class TestHoldUsability:
    def test_defaults(self):
        u = HoldUsability()
        assert u.left_hand is True
        assert u.quality_lh == 0.5

    def test_quality_bounds(self):
        with pytest.raises(ValidationError):
            HoldUsability(quality_lh=1.5)


class TestSurfaceNormal:
    def test_normalization(self):
        n = SurfaceNormal(dx=0.0, dy=0.0, dz=5.0)
        # After normalization, magnitude should be 1
        import math
        mag = math.sqrt(n.dx**2 + n.dy**2 + n.dz**2)
        assert abs(mag - 1.0) < 1e-6

    def test_zero_vector_fallback(self):
        n = SurfaceNormal(dx=0.0, dy=0.0, dz=0.0)
        assert n.dz == 1.0  # should fall back to pointing out from wall


# ---- Route models ----

class TestWallGeometry:
    def test_valid_creation(self):
        geom = WallGeometry(angle_degrees=0.0, wall_type=WallAngle.VERTICAL)
        assert geom.angle_degrees == 0.0

    def test_angle_bounds(self):
        with pytest.raises(ValidationError):
            WallGeometry(angle_degrees=100.0)


class TestClimbingRoute:
    def test_creation_minimal(self):
        geom = WallGeometry(angle_degrees=0.0)
        route = ClimbingRoute(
            id="route_1",
            wall_geometry=geom,
        )
        assert route.id == "route_1"
        assert route.holds == []

    def test_get_hold(self):
        geom = WallGeometry(angle_degrees=0.0)
        hold = make_test_hold()
        route = ClimbingRoute(id="r1", wall_geometry=geom, holds=[hold])
        assert route.get_hold("h1") is hold
        assert route.get_hold("nonexistent") is None


# ---- Climber model ----

class TestClimberProfile:
    def test_default_profile(self):
        profile = ClimberProfile.default_profile()
        assert profile.id == "default"
        assert profile.height_cm > 0
        assert profile.ape_index == profile.wingspan_cm - profile.height_cm

    def test_ape_index_computed(self):
        profile = ClimberProfile(
            id="test",
            height_cm=175.0,
            weight_kg=70.0,
            wingspan_cm=180.0,
            arm_length_cm=76.0,
            forearm_length_cm=36.0,
            leg_length_cm=90.0,
            torso_length_cm=55.0,
        )
        assert profile.ape_index == 5.0  # 180 - 175

    def test_max_reach_computed(self):
        profile = ClimberProfile.default_profile()
        assert profile.max_comfortable_reach_cm > 0
        assert profile.max_comfortable_reach_cm < 250  # sanity check

    def test_has_restriction_no_injuries(self):
        profile = ClimberProfile.default_profile()
        assert not profile.has_restriction("heel hook")

    def test_has_restriction_with_injury(self):
        from models.climber import Injury
        profile = ClimberProfile.default_profile()
        profile = profile.model_copy(update={
            "injuries": [
                Injury(body_part="knee", severity=0.5, movement_restrictions=["heel hook", "drop knee"])
            ]
        })
        assert profile.has_restriction("heel hook")
        assert not profile.has_restriction("crimp")


# ---- Beta models ----

class TestBetaSolution:
    def test_empty_beta(self):
        beta = BetaSolution(
            id="b1",
            beta_type=BetaType.HIGH_PERCENTAGE,
            climber_profile_id="p1",
            route_id="r1",
        )
        assert beta.move_count == 0
        assert beta.get_crux_moves() == []

    def test_crux_moves_identified(self):
        pos = HoldPosition(x=0.5, y=0.5, z_estimate=0.0)
        limb = LimbPosition(hold_id="h1", position=pos, is_on_wall=True)
        body = BodyPosition(
            left_hand=limb, right_hand=limb,
            left_foot=limb, right_foot=limb,
            center_of_mass=pos,
        )
        move = ClimbingMove(
            move_number=1,
            description="Test",
            move_types=[MoveType.STATIC],
            body_position=body,
            difficulty_rating=0.9,
            confidence=0.8,
            reasoning="Test",
            is_crux=True,
        )
        beta = BetaSolution(
            id="b1",
            beta_type=BetaType.HIGH_PERCENTAGE,
            climber_profile_id="p1",
            route_id="r1",
            moves=[move],
        )
        assert len(beta.get_crux_moves()) == 1


# ---- Coverage for all hold types ----

def test_all_hold_types_have_depth():
    for hold_type in HoldType:
        assert hold_type in HOLD_TYPE_DEPTH_CM, f"{hold_type} missing from HOLD_TYPE_DEPTH_CM"
        assert hold_type in HOLD_TYPE_FRICTION, f"{hold_type} missing from HOLD_TYPE_FRICTION"


def test_all_move_types_valid():
    # Ensure all MoveType enum values can be used
    assert len(list(MoveType)) > 30  # we have 33 move types
