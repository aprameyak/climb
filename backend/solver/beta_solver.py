from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from typing import Any

import anthropic

from biomechanics.body_model import HumanBodyModel
from biomechanics.movement_library import MovementLibrary
from models.beta import (
    BetaSolution,
    BetaType,
    BodyPosition,
    ClimbingMove,
    LimbPosition,
    MoveType,
)
from models.climber import ClimberProfile
from models.holds import DetectedHold, HoldPosition
from models.routes import ClimbingRoute, WallGeometry

from .beta_evaluator import BetaEvaluator
from .move_generator import MoveGenerator
from .route_graph import RouteGraphBuilder


_BETA_SOLVER_SYSTEM = """You are an elite climbing coach and movement specialist with 20+ years of experience at the highest competitive levels.

You analyze climbing routes and generate precise, biomechanically sound beta (movement sequences) personalized to the climber.

RULES:
1. Never recommend moves beyond the climber's physical capacity (reach, flexibility, strength)
2. Never ignore injuries — always route around them
3. Never assume the climber can dyno if their dynamic_comfort_score is below 0.3
4. Always explain WHY each move is made — the reasoning is as important as the move
5. Be conservative with confidence — climbing is complex; real uncertainty must be expressed
6. Foot placement is as important as hand placement — never neglect it
7. Body position (hips, torso rotation, weight distribution) is critical — always specify it

COORDINATE SYSTEM:
- Holds are in normalized (0-1) coordinates: x=0 left, x=1 right, y=0 top of wall, y=1 bottom
- Higher on the wall = lower y value
- Left hand / right hand from the climber's perspective (not viewer's)

Return ONLY a JSON object with this structure:
{
  "moves": [
    {
      "move_number": 1,
      "description": "Step on the left start hold with left foot, right foot on right start hold",
      "move_types": ["static"],
      "left_hand_hold_id": "h1",
      "right_hand_hold_id": "h2",
      "left_foot_hold_id": "h3",
      "right_foot_hold_id": "h4",
      "left_hand_flag": null,
      "right_hand_flag": null,
      "hips_x": 0.5,
      "hips_y": 0.7,
      "torso_rotation_deg": 0,
      "head_direction": "up",
      "weight_lh": 0.25,
      "weight_rh": 0.25,
      "weight_lf": 0.25,
      "weight_rf": 0.25,
      "difficulty_rating": 0.2,
      "confidence": 0.85,
      "reasoning": "Establish starting position on the two start holds. Left foot lower left, right foot lower right for stable base.",
      "common_mistakes": ["Stepping on wrong part of hold", "Starting with feet too low"],
      "alternative_options": ["Could swap hand/foot positions if more comfortable"],
      "energy_cost": 0.1,
      "risk_level": 0.05,
      "physics_note": null
    }
  ],
  "overall_confidence": 0.78,
  "notes": "This beta uses a backstep at move 4 to extend reach...",
  "warnings": ["Confidence reduced — move 6 has high reach requiring near-max span for this climber"],
  "crux_move_numbers": [4, 6]
}

For hold IDs: use the exact IDs provided. If a hand/foot is not on a hold (flagging, etc.), use null.
move_types must be from: static, deadpoint, controlled_dyno, full_dyno, hand_bump, hand_match, foot_match, drop_knee, backstep, inside_flag, outside_flag, reverse_flag, heel_hook, toe_hook, bicycle, scum, kneebar, rock_over, high_step, mantle, compression, stem, bridge, cross_through, cross_over, palm_press, campus_move, cut_loose, swing_control, hip_twist, hip_drive, shoulder_rotation, lockoff
Only return valid JSON — no markdown, no explanations outside JSON.
"""


def _holds_to_context(holds: list[DetectedHold]) -> str:
    """Format holds as a compact context string for the prompt."""
    lines: list[str] = []
    for h in holds:
        start_marker = " [START]" if h.is_start else ""
        finish_marker = " [FINISH]" if h.is_finish else ""
        line = (
            f"  {h.id}: {h.hold_type.value} at ({h.center.x:.2f},{h.center.y:.2f})"
            f" grip={h.grip_direction.value}"
            f" orient={h.orientation_degrees:.0f}°"
            f" friction={h.estimated_friction:.1f}"
            f" conf={h.confidence:.0f%}"
            f"{start_marker}{finish_marker}"
        )
        lines.append(line)
    return "\n".join(lines)


def _profile_to_context(profile: ClimberProfile) -> str:
    """Format climber profile as context string."""
    injuries = ", ".join(f"{i.body_part} (sev={i.severity:.0%})" for i in profile.injuries)
    return (
        f"  Height: {profile.height_cm:.0f}cm, Weight: {profile.weight_kg:.0f}kg\n"
        f"  Wingspan: {profile.wingspan_cm:.0f}cm (ape index: {profile.ape_index:+.0f}cm)\n"
        f"  Arm length: {profile.arm_length_cm:.0f}cm, Leg length: {profile.leg_length_cm:.0f}cm\n"
        f"  Max comfortable reach: {profile.max_comfortable_reach_cm:.0f}cm\n"
        f"  Shoulder mobility: {profile.shoulder_mobility_deg:.0f}°, Hip mobility: {profile.hip_mobility_deg:.0f}°\n"
        f"  Hamstring flexibility: {profile.hamstring_flexibility_score:.0%}\n"
        f"  Core: {profile.core_strength_score:.0%}, Fingers: {profile.finger_strength_score:.0%}, Crimp: {profile.crimp_strength_score:.0%}\n"
        f"  Sloper: {profile.sloper_ability_score:.0%}, Dynamic: {profile.dynamic_comfort_score:.0%}\n"
        f"  Fear of dynamic: {profile.fear_of_dynamic:.0%}\n"
        f"  Grade: V{profile.indoor_grade_v}, Style: {profile.preferred_style.value}, Level: {profile.experience_level.value}\n"
        f"  Injuries: {injuries or 'none'}\n"
        f"  Hand dominance: {profile.hand_dominance.value}"
    )


_BETA_TYPE_INSTRUCTIONS = {
    BetaType.SHORTEST: "Find the minimum number of moves to top the route. Prioritize directness over efficiency or elegance.",
    BetaType.TALL_CLIMBER: "Optimize for a tall climber (use the profile's height). Take longer reaches, avoid feet-first approaches that short climbers need.",
    BetaType.STATIC: "Every move must be static — no dynamic movement, deadpoints, or momentum. Prioritize control and precision.",
    BetaType.DYNAMIC: "Use dynamic movement where beneficial. Deadpoints and controlled dynos are encouraged. Generate momentum strategically.",
    BetaType.COMPETITION: "Competition-optimized — fastest sequence, high confidence, spectacular where appropriate. Assume peaked form.",
    BetaType.ENERGY_EFFICIENT: "Minimize total energy expenditure. Favor rests, shaking out, efficient foot work, and avoiding unnecessary moves.",
    BetaType.HIGH_PERCENTAGE: "Maximize probability of success. Favor well-established, reliable sequences over cutting-edge beta. Every move should be high-percentage.",
    BetaType.LOW_POWER: "Minimize strength requirements. Use technique, body position, and footwork to avoid pulling hard. Ideal for endurance or injury recovery.",
}


class BetaSolver:
    """AI-powered beta solver that generates personalized climbing movement sequences."""

    def __init__(self, anthropic_client: anthropic.Anthropic) -> None:
        self.client = anthropic_client
        self.graph_builder = RouteGraphBuilder()
        self.move_generator = MoveGenerator()
        self.movement_library = MovementLibrary()
        self.evaluator = BetaEvaluator()

    async def solve(
        self,
        route: ClimbingRoute,
        profile: ClimberProfile,
        beta_types: list[BetaType] | None = None,
    ) -> list[BetaSolution]:
        """Generate beta solutions for a route personalized to a climber.

        Args:
            route: The climbing route to solve.
            profile: Climber profile for personalization.
            beta_types: Which beta variants to generate. Defaults to high_percentage + energy_efficient.

        Returns:
            List of BetaSolution objects, one per beta type.
        """
        if beta_types is None:
            beta_types = [BetaType.HIGH_PERCENTAGE, BetaType.ENERGY_EFFICIENT]

        # Build body model for this climber
        body_model = HumanBodyModel(profile)

        # Build route graph
        route_graph = self.graph_builder.build_graph(route, profile, route.wall_geometry)

        solutions: list[BetaSolution] = []
        for beta_type in beta_types:
            try:
                solution = await self._solve_for_type(
                    route, profile, beta_type, body_model, route_graph
                )
                if solution:
                    # Evaluate and annotate crux moves
                    evaluation = self.evaluator.evaluate_beta(solution, profile, route)
                    solution.crux_move_numbers = evaluation.crux_move_numbers
                    solution.expected_send_probability = evaluation.estimated_send_probability
                    solution.expected_flash_probability = evaluation.estimated_flash_probability
                    for move in solution.moves:
                        move.is_crux = move.move_number in evaluation.crux_move_numbers
                    solutions.append(solution)
            except Exception as exc:
                # Log but don't crash — partial results are better than none
                partial = self._empty_solution(route, profile, beta_type)
                partial.generation_warnings.append(f"Beta generation failed: {exc!s}")
                solutions.append(partial)

        return solutions

    async def _solve_for_type(
        self,
        route: ClimbingRoute,
        profile: ClimberProfile,
        beta_type: BetaType,
        body_model: HumanBodyModel,
        route_graph,
    ) -> BetaSolution | None:
        """Generate a single beta solution for a specific beta type."""

        instruction = _BETA_TYPE_INSTRUCTIONS.get(beta_type, "Generate optimal beta.")
        holds_context = _holds_to_context(route.holds)
        profile_context = _profile_to_context(profile)

        user_prompt = (
            f"Generate {beta_type.value} beta for this climbing route.\n\n"
            f"BETA STYLE: {instruction}\n\n"
            f"WALL GEOMETRY:\n"
            f"  Angle: {route.wall_geometry.angle_degrees:.1f}° from vertical "
            f"({'slab' if route.wall_geometry.angle_degrees < -2 else 'overhang' if route.wall_geometry.angle_degrees > 2 else 'vertical'})\n"
            f"  Height: {route.wall_geometry.height_m:.1f}m, Width: {route.wall_geometry.width_m:.1f}m\n"
            f"  Volumes: {route.wall_geometry.has_volumes}\n\n"
            f"HOLDS:\n{holds_context}\n\n"
            f"Start holds: {route.start_holds}\n"
            f"Finish holds: {route.finish_holds}\n\n"
            f"CLIMBER PROFILE:\n{profile_context}\n\n"
            f"Generate a complete, move-by-move beta sequence from start holds to finish holds. "
            f"Include every hand and foot placement. "
            f"Be conservative with confidence. "
            f"Never recommend a move that exceeds the climber's physical limits. "
            f"Return only valid JSON."
        )

        message = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=_BETA_SOLVER_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = message.content[0].text
        data = self._parse_json(raw)
        return self._parse_solution(data, route, profile, beta_type)

    def _parse_json(self, text: str) -> dict[str, Any]:
        text = re.sub(r"```(?:json)?", "", text).strip()
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*]", "]", text)
        return json.loads(text)

    def _parse_solution(
        self,
        data: dict[str, Any],
        route: ClimbingRoute,
        profile: ClimberProfile,
        beta_type: BetaType,
    ) -> BetaSolution:
        """Parse Claude's response into a BetaSolution."""
        moves: list[ClimbingMove] = []
        warnings: list[str] = list(data.get("warnings", []))

        hold_map: dict[str, DetectedHold] = {h.id: h for h in route.holds}

        for raw_move in data.get("moves", []):
            try:
                move = self._parse_move(raw_move, hold_map, profile, route.wall_geometry)
                moves.append(move)
            except Exception as exc:
                warnings.append(f"Skipped move {raw_move.get('move_number', '?')}: {exc!s}")

        total_energy = sum(m.energy_cost for m in moves) / max(len(moves), 1)
        overall_conf = float(data.get("overall_confidence", 0.5))

        return BetaSolution(
            id=f"beta_{uuid.uuid4().hex[:8]}",
            beta_type=beta_type,
            climber_profile_id=profile.id,
            route_id=route.id,
            moves=moves,
            total_energy_cost=round(total_energy, 3),
            overall_confidence=overall_conf,
            notes=data.get("notes", ""),
            crux_move_numbers=data.get("crux_move_numbers", []),
            generated_at=datetime.utcnow(),
            generation_warnings=warnings,
        )

    def _parse_move(
        self,
        raw: dict[str, Any],
        hold_map: dict[str, DetectedHold],
        profile: ClimberProfile,
        wall_geometry: WallGeometry,
    ) -> ClimbingMove:
        """Parse a single move from the raw response."""

        def get_limb(hold_id_key: str, flag_key: str | None = None) -> LimbPosition:
            hid = raw.get(hold_id_key)
            flag = raw.get(flag_key) if flag_key else None
            if hid and hid in hold_map:
                hold = hold_map[hid]
                return LimbPosition(
                    hold_id=hid,
                    position=hold.center,
                    is_on_wall=True,
                    flag_type=flag,
                )
            return LimbPosition(
                hold_id=None,
                position=None,
                is_on_wall=flag is None,
                flag_type=flag,
            )

        lh = get_limb("left_hand_hold_id", "left_hand_flag")
        rh = get_limb("right_hand_hold_id", "right_hand_flag")
        lf = get_limb("left_foot_hold_id")
        rf = get_limb("right_foot_hold_id")

        # Weight distribution
        weight = {
            "lh": float(raw.get("weight_lh", 0.25)),
            "rh": float(raw.get("weight_rh", 0.25)),
            "lf": float(raw.get("weight_lf", 0.25)),
            "rf": float(raw.get("weight_rf", 0.25)),
        }
        total_w = sum(weight.values())
        if total_w > 0:
            weight = {k: v / total_w for k, v in weight.items()}

        # COM estimate
        hip_x = float(raw.get("hips_x", 0.5))
        hip_y = float(raw.get("hips_y", 0.6))

        body_pos = BodyPosition(
            left_hand=lh,
            right_hand=rh,
            left_foot=lf,
            right_foot=rf,
            hips_position=HoldPosition(x=hip_x, y=hip_y, z_estimate=0.0),
            torso_rotation_deg=float(raw.get("torso_rotation_deg", 0.0)),
            head_direction=raw.get("head_direction", "up"),
            weight_distribution=weight,
            center_of_mass=HoldPosition(x=hip_x, y=hip_y - 0.05, z_estimate=0.0),
        )

        # Parse move types
        move_type_strs: list[str] = raw.get("move_types", ["static"])
        move_types: list[MoveType] = []
        for mt_str in move_type_strs:
            try:
                move_types.append(MoveType(mt_str))
            except ValueError:
                pass
        if not move_types:
            move_types = [MoveType.STATIC]

        return ClimbingMove(
            move_number=int(raw.get("move_number", 1)),
            description=raw.get("description", ""),
            move_types=move_types,
            body_position=body_pos,
            difficulty_rating=float(raw.get("difficulty_rating", 0.5)),
            confidence=float(raw.get("confidence", 0.5)),
            reasoning=raw.get("reasoning", ""),
            common_mistakes=raw.get("common_mistakes", []),
            alternative_options=raw.get("alternative_options", []),
            energy_cost=float(raw.get("energy_cost", 0.3)),
            risk_level=float(raw.get("risk_level", 0.1)),
            physics_note=raw.get("physics_note"),
        )

    def _empty_solution(
        self, route: ClimbingRoute, profile: ClimberProfile, beta_type: BetaType
    ) -> BetaSolution:
        return BetaSolution(
            id=f"beta_{uuid.uuid4().hex[:8]}",
            beta_type=beta_type,
            climber_profile_id=profile.id,
            route_id=route.id,
            moves=[],
            total_energy_cost=0.0,
            overall_confidence=0.0,
            notes="Beta generation encountered an error.",
            generated_at=datetime.utcnow(),
        )
