from __future__ import annotations

import math

import numpy as np

from models.holds import DetectedHold, HoldType


# Static friction coefficients for rubber shoe sole on climbing hold materials
# Values estimated from empirical testing data
RUBBER_FRICTION: dict[HoldType, float] = {
    HoldType.JUG: 0.90,
    HoldType.POSITIVE_EDGE: 0.80,
    HoldType.INCUT: 0.82,
    HoldType.FLAT_EDGE: 0.60,
    HoldType.CRIMP: 0.65,
    HoldType.MICRO_CRIMP: 0.55,
    HoldType.POCKET: 0.78,
    HoldType.MONO: 0.70,
    HoldType.POCKET_2F: 0.74,
    HoldType.POCKET_3F: 0.76,
    HoldType.SLOPER: 0.50,  # highly angle-dependent
    HoldType.PINCH: 0.72,
    HoldType.RAIL: 0.65,
    HoldType.HORN: 0.82,
    HoldType.SIDEPULL: 0.72,
    HoldType.UNDERCLING: 0.70,
    HoldType.GASTON: 0.68,
    HoldType.VOLUME: 0.62,
    HoldType.SCREW_ON: 0.70,
    HoldType.CHIP: 0.55,
    HoldType.FOOT_CHIP: 0.58,
    HoldType.SMEAR: 0.52,
    HoldType.MACRO: 0.68,
    HoldType.DUAL_TEXTURE: 0.72,
    HoldType.UNKNOWN: 0.65,
}


class FrictionModel:
    """Physics-based friction analysis for climbing holds and wall surfaces."""

    def estimate_hold_friction(
        self,
        hold: DetectedHold,
        wall_angle_deg: float,
        chalk_factor: float = 1.0,
        temperature_factor: float = 1.0,
    ) -> float:
        """Estimate effective friction coefficient for a hold.

        Args:
            hold: The detected hold.
            wall_angle_deg: Wall angle affects how friction interacts with gravity.
            chalk_factor: Effect of chalk (1.0=freshly chalked, 0.7=polished/no chalk).
            temperature_factor: Cold temps increase friction (1.0=20°C, 1.1=10°C, 0.9=30°C).

        Returns:
            Effective friction coefficient (higher = better grip).
        """
        base_friction = RUBBER_FRICTION.get(hold.hold_type, 0.65)

        # Sloper friction is highly angle-dependent
        if hold.hold_type == HoldType.SLOPER:
            # Optimal sloper angle: hold orientation perpendicular to force vector
            # Beyond ~30° from optimal, friction drops rapidly
            wall_rad = math.radians(wall_angle_deg)
            orientation_rad = math.radians(hold.orientation_degrees)
            # Simplified: friction peaks when hold faces climber directly
            angle_factor = math.cos(orientation_rad - wall_rad) * 0.5 + 0.5
            base_friction *= angle_factor

        # Wall angle effect: steeper overhangs increase normal force requirement
        if wall_angle_deg > 30:
            # Higher overhang increases the component of gravity pulling climber off wall
            overhang_penalty = (wall_angle_deg - 30) / 60.0 * 0.15
            base_friction -= overhang_penalty

        # Apply modifiers
        effective_friction = base_friction * chalk_factor * temperature_factor

        return round(max(0.1, min(1.0, effective_friction)), 3)

    def compute_slip_risk(
        self,
        hold: DetectedHold,
        wall_angle_deg: float,
        force_direction: np.ndarray,
        body_weight_kg: float = 68.0,
    ) -> float:
        """Estimate probability of foot or hand slipping from hold.

        Args:
            hold: The hold being loaded.
            wall_angle_deg: Wall angle in degrees.
            force_direction: Unit vector of applied force.
            body_weight_kg: Climber's body weight for force estimation.

        Returns:
            Slip probability (0=no risk, 1=certain slip).
        """
        friction = self.estimate_hold_friction(hold, wall_angle_deg)

        # Normal force component (perpendicular to hold surface)
        normal = np.array([hold.surface_normal.dx, hold.surface_normal.dy, hold.surface_normal.dz])
        if np.linalg.norm(normal) < 1e-6:
            normal = np.array([0, 0, 1.0])

        normal_component = abs(float(np.dot(force_direction, normal)))
        tangential_component = math.sqrt(max(0, 1.0 - normal_component**2))

        # Coulomb friction: slip when tangential > friction_coeff × normal
        gravity_force = body_weight_kg * 9.81  # N
        normal_force = normal_component * gravity_force
        tangential_force = tangential_component * gravity_force

        if normal_force < 1.0:
            # Very little normal force = slipping regardless
            return 0.85

        safety_factor = (friction * normal_force) / (tangential_force + 1e-6)
        # slip_risk: 0 when safety_factor >> 1, 1 when safety_factor < 1
        risk = max(0.0, 1.0 - (safety_factor - 1.0) / 2.0)
        return round(min(1.0, max(0.0, risk)), 3)

    def estimate_rubber_friction(
        self,
        hold_type: HoldType,
        wall_angle_deg: float,
        shoe_age_factor: float = 1.0,
    ) -> float:
        """Estimate rubber-on-hold friction for footwork analysis.

        shoe_age_factor: 1.0 = fresh rubber, 0.7 = worn-out shoes.
        """
        base = RUBBER_FRICTION.get(hold_type, 0.65)

        # Rubber friction on slab: very high (smearing)
        if wall_angle_deg < 0:
            slab_bonus = abs(wall_angle_deg) / 20.0 * 0.15
            base += slab_bonus

        # On overhang: foothold friction becomes critical
        if wall_angle_deg > 30:
            overhang_penalty = (wall_angle_deg - 30) / 60.0 * 0.2
            base -= overhang_penalty

        return round(max(0.1, min(1.0, base * shoe_age_factor)), 3)
