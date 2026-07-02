from __future__ import annotations

import math
from typing import Iterator

from models.climber import ClimberProfile
from models.holds import DetectedHold, HoldType
from models.routes import ClimbingRoute, EdgeType, RouteEdge, RouteGraph, WallGeometry
from biomechanics.reach_model import ReachModel


class RouteGraphBuilder:
    """Builds a weighted graph of possible transitions between holds."""

    # Maximum normalized distance to consider a transition possible at all
    MAX_NORMALIZED_DISTANCE = 0.65

    def __init__(self) -> None:
        self.reach_model = ReachModel()

    def build_graph(
        self,
        route: ClimbingRoute,
        profile: ClimberProfile,
        wall_geometry: WallGeometry,
    ) -> RouteGraph:
        """Build complete route graph for a climber.

        For each pair of holds, compute whether a hand-to-hand or foot-to-hand
        transition is physically possible for this climber, and estimate the
        properties of each transition.

        Args:
            route: The climbing route with all holds.
            profile: Climber profile for reach/strength constraints.
            wall_geometry: Wall angle and dimensions.

        Returns:
            RouteGraph with nodes and weighted edges.
        """
        holds = route.holds
        nodes: dict[str, DetectedHold] = {h.id: h for h in holds}
        edges: list[RouteEdge] = []

        for i, from_hold in enumerate(holds):
            for j, to_hold in enumerate(holds):
                if i == j:
                    continue

                # Only consider upward or lateral transitions for hands
                # (downward moves are unusual except for feet)
                distance = self._normalized_distance(from_hold, to_hold)
                if distance > self.MAX_NORMALIZED_DISTANCE:
                    continue

                # Hand-to-hand edge
                hand_edge = self._compute_hand_edge(
                    from_hold, to_hold, profile, wall_geometry, distance
                )
                if hand_edge is not None:
                    edges.append(hand_edge)

                # Foot-to-foot edge (more liberal distance)
                if distance <= 0.45:
                    foot_edge = self._compute_foot_edge(
                        from_hold, to_hold, profile, wall_geometry, distance
                    )
                    if foot_edge is not None:
                        edges.append(foot_edge)

        return RouteGraph(nodes=nodes, edges=edges)

    def _compute_hand_edge(
        self,
        from_hold: DetectedHold,
        to_hold: DetectedHold,
        profile: ClimberProfile,
        wall_geometry: WallGeometry,
        distance: float,
    ) -> RouteEdge | None:
        """Compute a hand-to-hand transition edge if feasible."""
        if not (to_hold.usability.left_hand or to_hold.usability.right_hand):
            return None

        # Estimate required reach in cm
        required_reach_cm = distance * wall_geometry.width_m * 100

        # Check if within climber's max reach
        reach_vol = self.reach_model.compute_reach_volume(profile, wall_geometry.angle_degrees)
        if required_reach_cm > reach_vol.max_reach_cm:
            # Still include edge with low confidence — deadpoint/dyno might make it possible
            momentum_required = True
            conf = 0.3
        else:
            momentum_required = required_reach_cm > reach_vol.comfortable_reach_cm
            conf = 0.8 - (required_reach_cm / reach_vol.max_reach_cm) * 0.4

        # Height difference — preferring upward moves
        dy = from_hold.center.y - to_hold.center.y  # positive = to_hold is above from_hold
        dx = abs(to_hold.center.x - from_hold.center.x)

        # Lateral moves on steep overhangs are harder
        overhang_penalty = max(0, wall_geometry.angle_degrees) / 90.0 * 0.2

        # Estimate required body positions
        hip_rotation_needed = math.degrees(math.atan2(dx, max(dy, 0.01))) * 0.3
        shoulder_rotation = 10.0 if dx > 0.1 else 0.0

        # Difficulty based on hold quality and reach
        from_difficulty = self._hold_difficulty_factor(from_hold)
        to_difficulty = self._hold_difficulty_factor(to_hold)
        reach_difficulty = (required_reach_cm / max(reach_vol.comfortable_reach_cm, 1)) * 0.5
        edge_difficulty = min(10.0, (from_difficulty + to_difficulty) / 2 + reach_difficulty * 3)

        body_hint = self._compute_body_position_hint(from_hold, to_hold, wall_geometry)

        return RouteEdge(
            from_hold_id=from_hold.id,
            to_hold_id=to_hold.id,
            edge_type=EdgeType.HAND_TO_HAND,
            required_reach_cm=round(required_reach_cm, 1),
            required_hip_rotation_deg=round(hip_rotation_needed, 1),
            required_shoulder_rotation_deg=round(shoulder_rotation, 1),
            required_knee_flexion_deg=0.0,
            body_position_hint=body_hint,
            momentum_required=momentum_required,
            estimated_difficulty=round(edge_difficulty, 2),
            risk_level=round(min(0.9, reach_difficulty * 0.5 + overhang_penalty), 2),
            energy_cost=round(min(0.95, reach_difficulty * 0.4 + overhang_penalty + from_difficulty * 0.2), 2),
            confidence=round(conf, 2),
        )

    def _compute_foot_edge(
        self,
        from_hold: DetectedHold,
        to_hold: DetectedHold,
        profile: ClimberProfile,
        wall_geometry: WallGeometry,
        distance: float,
    ) -> RouteEdge | None:
        """Compute a foot-to-foot transition edge if feasible."""
        if not (to_hold.usability.left_foot or to_hold.usability.right_foot):
            return None

        required_reach_cm = distance * wall_geometry.height_m * 100
        max_foot_dist = self.reach_model.compute_max_step_height(profile) * 1.5

        if required_reach_cm > max_foot_dist:
            return None

        difficulty = min(10.0, (required_reach_cm / max_foot_dist) * 5.0)
        conf = 0.75 - (required_reach_cm / max_foot_dist) * 0.3

        return RouteEdge(
            from_hold_id=from_hold.id,
            to_hold_id=to_hold.id,
            edge_type=EdgeType.FOOT_TO_FOOT,
            required_reach_cm=round(required_reach_cm, 1),
            required_hip_rotation_deg=0.0,
            required_shoulder_rotation_deg=0.0,
            required_knee_flexion_deg=50.0,
            body_position_hint="Precise foot placement",
            momentum_required=False,
            estimated_difficulty=round(difficulty, 2),
            risk_level=0.1,
            energy_cost=0.15,
            confidence=round(conf, 2),
        )

    def _normalized_distance(self, a: DetectedHold, b: DetectedHold) -> float:
        """Euclidean distance between hold centers in normalized coords."""
        dx = a.center.x - b.center.x
        dy = a.center.y - b.center.y
        return math.sqrt(dx**2 + dy**2)

    def _hold_difficulty_factor(self, hold: DetectedHold) -> float:
        """0-1 difficulty factor based on hold type."""
        DIFFICULTY_MAP = {
            HoldType.JUG: 0.1,
            HoldType.POSITIVE_EDGE: 0.25,
            HoldType.INCUT: 0.3,
            HoldType.HORN: 0.15,
            HoldType.RAIL: 0.3,
            HoldType.FLAT_EDGE: 0.55,
            HoldType.CRIMP: 0.65,
            HoldType.MICRO_CRIMP: 0.80,
            HoldType.POCKET: 0.5,
            HoldType.MONO: 0.9,
            HoldType.POCKET_2F: 0.7,
            HoldType.POCKET_3F: 0.55,
            HoldType.SLOPER: 0.7,
            HoldType.PINCH: 0.6,
            HoldType.SIDEPULL: 0.5,
            HoldType.UNDERCLING: 0.55,
            HoldType.GASTON: 0.6,
            HoldType.VOLUME: 0.5,
            HoldType.SCREW_ON: 0.45,
            HoldType.CHIP: 0.55,
            HoldType.FOOT_CHIP: 0.3,
            HoldType.SMEAR: 0.7,
            HoldType.MACRO: 0.35,
            HoldType.DUAL_TEXTURE: 0.5,
            HoldType.UNKNOWN: 0.5,
        }
        return DIFFICULTY_MAP.get(hold.hold_type, 0.5)

    def _compute_body_position_hint(
        self,
        from_hold: DetectedHold,
        to_hold: DetectedHold,
        wall_geometry: WallGeometry,
    ) -> str:
        """Generate a body position hint for this transition."""
        dx = to_hold.center.x - from_hold.center.x
        dy = from_hold.center.y - to_hold.center.y  # positive = to_hold is above

        parts: list[str] = []

        if abs(dx) > 0.15:
            parts.append("backstep" if abs(dx) > 0.25 else "hip rotation")

        if dy > 0.15:
            parts.append("high reach — lock off or deadpoint")
        elif dy < -0.05:
            parts.append("downward reach")

        if wall_geometry.angle_degrees > 20:
            parts.append("keep hips close to wall")

        return "; ".join(parts) if parts else "standard movement"
