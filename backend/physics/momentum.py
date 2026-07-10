from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class MomentumResult:
    """Result of a momentum calculation."""

    peak_velocity_ms: float  # Peak velocity at apex
    time_to_target_ms: float  # Time from launch to target
    required_launch_velocity_ms: float  # Launch velocity needed
    estimated_success_rate: float  # Probability of catching target hold (0-1)
    optimal_launch_angle_deg: float  # Best angle to launch
    energy_required_j: float  # Energy in joules
    feasible: bool  # Whether the move is physically possible
    limiting_factor: str  # What limits this move


class MomentumModel:
    """Physics-based model for dynamic climbing movements."""

    G = 9.81  # m/s²

    def compute_deadpoint(
        self,
        from_pos: np.ndarray,  # normalized wall coords
        to_pos: np.ndarray,
        body_mass_kg: float,
        wall_angle_deg: float,
        wall_height_m: float = 4.0,
        wall_width_m: float = 3.0,
    ) -> MomentumResult:
        """Compute physics of a deadpoint move.

        A deadpoint catches a hold at the apex of an upward movement
        (where velocity is momentarily zero = "dead").

        Args:
            from_pos: Starting position in normalized wall coordinates.
            to_pos: Target hold position in normalized wall coordinates.
            body_mass_kg: Climber's mass.
            wall_angle_deg: Wall angle (affects gravity component).
            wall_height_m: Real wall height in meters.
            wall_width_m: Real wall width in meters.

        Returns:
            MomentumResult with all computed physics.
        """
        dx = (to_pos[0] - from_pos[0]) * wall_width_m
        dy = (from_pos[1] - to_pos[1]) * wall_height_m  # flip y (up = positive)

        distance = math.sqrt(dx**2 + dy**2)

        if distance < 0.05:  # Less than 5cm — static move
            return MomentumResult(
                peak_velocity_ms=0.0,
                time_to_target_ms=500.0,
                required_launch_velocity_ms=0.0,
                estimated_success_rate=0.9,
                optimal_launch_angle_deg=90.0,
                energy_required_j=0.0,
                feasible=True,
                limiting_factor="none",
            )

        wall_rad = math.radians(wall_angle_deg)
        g_along_wall = self.G * math.sin(wall_rad)
        g_effective = self.G * math.cos(math.radians(max(0, wall_angle_deg)))

        # For deadpoint: need to reach height dy with zero velocity at apex
        # v² = 2 × g_effective × dy => v = sqrt(2 × g × dy)
        if dy <= 0:
            # Target is below or same height — deadpoint not needed
            return MomentumResult(
                peak_velocity_ms=0.0,
                time_to_target_ms=300.0,
                required_launch_velocity_ms=0.0,
                estimated_success_rate=0.8,
                optimal_launch_angle_deg=45.0,
                energy_required_j=0.0,
                feasible=True,
                limiting_factor="none",
            )

        required_v = math.sqrt(2 * g_effective * dy)
        time_to_apex = required_v / g_effective
        time_to_target_ms = time_to_apex * 1000

        if abs(dx) < 0.01:
            launch_angle = 90.0
        else:
            launch_angle = math.degrees(math.atan2(dy, abs(dx)))

        energy = 0.5 * body_mass_kg * required_v**2

        # Larger holds = more forgiving, faster velocity = less time to adjust
        timing_window_ms = max(50, 200 - required_v * 50)
        success_rate = min(0.95, 0.4 + timing_window_ms / 300.0)

        MAX_FEASIBLE_V = 4.5
        feasible = required_v <= MAX_FEASIBLE_V

        return MomentumResult(
            peak_velocity_ms=round(required_v, 2),
            time_to_target_ms=round(time_to_target_ms, 0),
            required_launch_velocity_ms=round(required_v, 2),
            estimated_success_rate=round(success_rate, 3),
            optimal_launch_angle_deg=round(launch_angle, 1),
            energy_required_j=round(energy, 1),
            feasible=feasible,
            limiting_factor="none" if feasible else "velocity_limit",
        )

    def compute_dyno(
        self,
        from_pos: np.ndarray,
        to_pos: np.ndarray,
        body_mass_kg: float,
        wall_angle_deg: float,
        wall_height_m: float = 4.0,
        wall_width_m: float = 3.0,
    ) -> MomentumResult:
        """Compute physics of a full dyno (both feet leave wall).

        This is more demanding than a deadpoint — the climber is fully airborne.
        """
        deadpoint_result = self.compute_deadpoint(
            from_pos, to_pos, body_mass_kg, wall_angle_deg, wall_height_m, wall_width_m
        )

        return MomentumResult(
            peak_velocity_ms=deadpoint_result.peak_velocity_ms * 1.2,
            time_to_target_ms=deadpoint_result.time_to_target_ms * 1.1,
            required_launch_velocity_ms=deadpoint_result.required_launch_velocity_ms * 1.2,
            estimated_success_rate=deadpoint_result.estimated_success_rate * 0.75,
            optimal_launch_angle_deg=deadpoint_result.optimal_launch_angle_deg,
            energy_required_j=deadpoint_result.energy_required_j * 1.5,
            feasible=deadpoint_result.feasible and deadpoint_result.required_launch_velocity_ms <= 3.5,
            limiting_factor=deadpoint_result.limiting_factor,
        )

    def is_deadpoint_needed(
        self,
        from_hold: object,  # DetectedHold
        to_hold: object,  # DetectedHold
        profile: object,  # ClimberProfile
        wall_angle_deg: float,
    ) -> bool:
        """Determine if a deadpoint is needed for a given transition.

        A deadpoint is needed when the target hold is beyond comfortable
        static reach but within dynamic reach.
        """
        from biomechanics.reach_model import ReachModel

        reach_model = ReachModel()
        reach_vol = reach_model.compute_reach_volume(profile, wall_angle_deg)  # type: ignore[arg-type]

        from_center = from_hold.center  # type: ignore[attr-defined]
        to_center = to_hold.center  # type: ignore[attr-defined]

        dx = (to_center.x - from_center.x) * 300  # approx cm
        dy = (from_center.y - to_center.y) * 400  # cm
        distance_cm = math.sqrt(dx**2 + dy**2)

        return (
            distance_cm > reach_vol.comfortable_reach_cm
            and distance_cm <= reach_vol.max_reach_cm * 1.3
        )

    def estimate_launch_angle(
        self, from_pos: np.ndarray, to_pos: np.ndarray, wall_angle_deg: float
    ) -> float:
        """Estimate optimal launch angle for a dynamic move."""
        dx = to_pos[0] - from_pos[0]
        dy = from_pos[1] - to_pos[1]  # up = positive

        if abs(dy) < 1e-6:
            return 45.0  # purely lateral
        if abs(dx) < 1e-6:
            return 90.0  # purely vertical

        angle = math.degrees(math.atan2(abs(dy), abs(dx)))

        if wall_angle_deg > 20:
            angle *= 1.0 - (wall_angle_deg - 20) / 70.0 * 0.3

        return round(max(20.0, min(85.0, angle)), 1)
