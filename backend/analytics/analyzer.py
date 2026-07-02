from __future__ import annotations

from models.analysis import AnalysisResult, DifficultyAnalysis
from models.beta import BetaSolution, MoveType
from models.holds import DetectedHold, HoldType
from models.routes import ClimbingRoute


# V-grade to Fontainebleau mapping
V_TO_FONT: dict[int, str] = {
    0: "4", 1: "4+/5a", 2: "5a/5b", 3: "5b/5c", 4: "5c/6a", 5: "6a+",
    6: "6b", 7: "6b+/6c", 8: "6c+/7a", 9: "7a+", 10: "7b",
    11: "7b+", 12: "7c", 13: "7c+", 14: "8a", 15: "8a+", 16: "8b", 17: "8b+",
}


class AnalyticsService:
    """Computes difficulty analysis and aggregate statistics."""

    def compute_difficulty_analysis(
        self,
        route: ClimbingRoute,
        betas: list[BetaSolution],
    ) -> DifficultyAnalysis:
        """Estimate difficulty metrics for a climbing route.

        Uses hold types, route graph structure, and beta data to
        estimate grade and intensity metrics.

        Args:
            route: The climbing route.
            betas: Generated beta solutions.

        Returns:
            DifficultyAnalysis with grade estimate and intensity breakdown.
        """
        holds = route.holds
        if not holds:
            return self._default_difficulty()

        # --- Grade estimate from hold types ---
        grade_v = self._estimate_grade(holds, route.wall_geometry.angle_degrees)

        # --- Crux description ---
        crux_desc = self._describe_crux(betas, holds)

        # --- Intensity metrics ---
        power_intensity = self._compute_power_intensity(holds, route.wall_geometry.angle_degrees)
        finger_intensity = self._compute_finger_intensity(holds)
        core_intensity = self._compute_core_intensity(betas, route.wall_geometry.angle_degrees)
        coordination_intensity = self._compute_coordination_intensity(betas)
        balance_intensity = self._compute_balance_intensity(betas, route.wall_geometry.angle_degrees)
        mobility_intensity = self._compute_mobility_intensity(betas)
        risk_level = self._compute_risk_level(betas, route.wall_geometry.angle_degrees)

        # --- Send probabilities ---
        if betas:
            flash_prob = sum(b.expected_flash_probability for b in betas) / len(betas)
            send_prob = sum(b.expected_send_probability for b in betas) / len(betas)
        else:
            flash_prob = 0.3
            send_prob = 0.7

        return DifficultyAnalysis(
            grade_v_estimate=grade_v,
            grade_font_estimate=V_TO_FONT.get(grade_v, f"V{grade_v}"),
            crux_description=crux_desc,
            power_intensity=round(power_intensity, 3),
            finger_intensity=round(finger_intensity, 3),
            core_intensity=round(core_intensity, 3),
            coordination_intensity=round(coordination_intensity, 3),
            balance_intensity=round(balance_intensity, 3),
            mobility_intensity=round(mobility_intensity, 3),
            risk_level=round(risk_level, 3),
            flash_probability=round(flash_prob, 3),
            send_probability=round(send_prob, 3),
            confidence=min(0.8, sum(h.confidence for h in holds) / len(holds)),
        )

    def _estimate_grade(self, holds: list[DetectedHold], wall_angle_deg: float) -> int:
        """Estimate V-grade from hold types and wall angle."""
        if not holds:
            return 4  # default unknown

        # Grade contributions from hold types
        HOLD_GRADE_CONTRIBUTION: dict[HoldType, float] = {
            HoldType.JUG: 1.0,
            HoldType.POSITIVE_EDGE: 2.5,
            HoldType.INCUT: 3.0,
            HoldType.FLAT_EDGE: 5.5,
            HoldType.CRIMP: 7.0,
            HoldType.MICRO_CRIMP: 9.5,
            HoldType.SLOPER: 7.5,
            HoldType.MONO: 10.0,
            HoldType.POCKET: 4.5,
            HoldType.POCKET_2F: 7.0,
            HoldType.POCKET_3F: 5.5,
            HoldType.PINCH: 6.0,
            HoldType.GASTON: 6.5,
            HoldType.UNDERCLING: 5.5,
            HoldType.SIDEPULL: 5.0,
            HoldType.RAIL: 4.0,
            HoldType.HORN: 2.5,
            HoldType.VOLUME: 4.5,
            HoldType.SCREW_ON: 3.5,
            HoldType.CHIP: 6.0,
            HoldType.FOOT_CHIP: 3.0,
            HoldType.SMEAR: 5.5,
            HoldType.MACRO: 3.0,
            HoldType.DUAL_TEXTURE: 4.0,
            HoldType.UNKNOWN: 4.0,
        }

        # Use hardest holds (top 30%) to estimate crux grade
        contributions = sorted(
            [HOLD_GRADE_CONTRIBUTION.get(h.hold_type, 4.0) for h in holds],
            reverse=True,
        )
        top_count = max(1, len(contributions) // 3)
        crux_grade = sum(contributions[:top_count]) / top_count

        # Wall angle modifier
        if wall_angle_deg > 20:
            crux_grade += (wall_angle_deg - 20) / 30.0 * 1.5
        elif wall_angle_deg < 0:
            # Slab adds technique difficulty
            crux_grade += abs(wall_angle_deg) / 20.0 * 0.8

        grade_v = int(round(crux_grade))
        return max(0, min(17, grade_v))

    def _describe_crux(
        self, betas: list[BetaSolution], holds: list[DetectedHold]
    ) -> str:
        """Generate a textual description of the crux."""
        if not betas:
            return "Crux cannot be determined without beta analysis."

        crux_moves = []
        for beta in betas:
            crux_moves.extend([m for m in beta.moves if m.is_crux])

        if not crux_moves:
            # Fall back to describing hardest hold
            if holds:
                hardest = max(holds, key=lambda h: h.estimated_difficulty)
                return f"Route crux likely involves the {hardest.hold_type.value} at position ({hardest.center.x:.2f}, {hardest.center.y:.2f})"
            return "Crux not identified"

        # Summarize crux moves
        crux_types = set()
        for move in crux_moves[:3]:
            for mt in move.move_types:
                crux_types.add(mt.value.replace("_", " "))

        techniques = ", ".join(list(crux_types)[:3])
        return f"Crux involves {techniques} — {crux_moves[0].description if crux_moves else 'difficult sequence'}"

    def _compute_power_intensity(self, holds: list[DetectedHold], wall_angle_deg: float) -> float:
        """How much raw power is needed (0-1)."""
        # Power = average friction resistance × wall angle factor
        avg_friction = sum(1.0 - h.estimated_friction for h in holds) / max(len(holds), 1)
        angle_factor = max(0, wall_angle_deg) / 90.0
        return min(1.0, avg_friction * 0.5 + angle_factor * 0.5)

    def _compute_finger_intensity(self, holds: list[DetectedHold]) -> float:
        """Finger strength demand (0-1)."""
        FINGER_DEMAND: dict[HoldType, float] = {
            HoldType.CRIMP: 0.9, HoldType.MICRO_CRIMP: 1.0, HoldType.MONO: 1.0,
            HoldType.POCKET_2F: 0.8, HoldType.POCKET: 0.65, HoldType.POCKET_3F: 0.7,
            HoldType.CHIP: 0.75, HoldType.FLAT_EDGE: 0.7, HoldType.SLOPER: 0.6,
            HoldType.PINCH: 0.65, HoldType.JUG: 0.2, HoldType.INCUT: 0.45,
        }
        demands = [FINGER_DEMAND.get(h.hold_type, 0.5) for h in holds]
        if not demands:
            return 0.5
        # Weight top 25% (crux demands)
        demands.sort(reverse=True)
        top = demands[:max(1, len(demands) // 4)]
        return min(1.0, sum(top) / len(top))

    def _compute_core_intensity(self, betas: list[BetaSolution], wall_angle_deg: float) -> float:
        """Core engagement required (0-1)."""
        angle_core = max(0, wall_angle_deg) / 90.0 * 0.6
        if not betas:
            return angle_core

        high_core_moves = {
            MoveType.COMPRESSION, MoveType.CUT_LOOSE, MoveType.SWING_CONTROL,
            MoveType.FULL_DYNO, MoveType.CAMPUS_MOVE, MoveType.MANTLE,
        }
        total_moves = sum(len(b.moves) for b in betas)
        if total_moves == 0:
            return angle_core

        core_move_count = sum(
            1 for b in betas for m in b.moves
            if any(mt in high_core_moves for mt in m.move_types)
        )
        move_factor = core_move_count / total_moves * 0.4
        return min(1.0, angle_core + move_factor)

    def _compute_coordination_intensity(self, betas: list[BetaSolution]) -> float:
        """Coordination and timing required (0-1)."""
        if not betas:
            return 0.4

        dynamic_types = {
            MoveType.DEADPOINT, MoveType.CONTROLLED_DYNO, MoveType.FULL_DYNO,
            MoveType.HEEL_HOOK, MoveType.TOE_HOOK, MoveType.CROSS_THROUGH,
            MoveType.CROSS_OVER, MoveType.BICYCLE,
        }
        total = sum(len(b.moves) for b in betas)
        if total == 0:
            return 0.4

        coord_count = sum(
            1 for b in betas for m in b.moves
            if any(mt in dynamic_types for mt in m.move_types)
        )
        return min(1.0, 0.3 + coord_count / total * 0.7)

    def _compute_balance_intensity(self, betas: list[BetaSolution], wall_angle_deg: float) -> float:
        """Balance difficulty (0-1)."""
        # Slab requires most balance
        if wall_angle_deg < 0:
            return min(1.0, abs(wall_angle_deg) / 20.0 * 0.8 + 0.2)

        # Overhang: balancing while upside-down
        if wall_angle_deg > 35:
            return 0.5 + (wall_angle_deg - 35) / 55.0 * 0.3

        return 0.3 + wall_angle_deg / 90.0 * 0.2

    def _compute_mobility_intensity(self, betas: list[BetaSolution]) -> float:
        """Flexibility/mobility required (0-1)."""
        if not betas:
            return 0.3

        mobility_types = {
            MoveType.HEEL_HOOK, MoveType.TOE_HOOK, MoveType.HIGH_STEP,
            MoveType.ROCK_OVER, MoveType.KNEEBAR, MoveType.STEM,
        }
        total = sum(len(b.moves) for b in betas)
        if total == 0:
            return 0.3

        mobility_count = sum(
            1 for b in betas for m in b.moves
            if any(mt in mobility_types for mt in m.move_types)
        )
        return min(1.0, 0.2 + mobility_count / total * 0.8)

    def _compute_risk_level(self, betas: list[BetaSolution], wall_angle_deg: float) -> float:
        """Overall risk level (0-1)."""
        if not betas:
            return 0.2 + max(0, wall_angle_deg) / 90.0 * 0.3

        avg_risk = sum(m.risk_level for b in betas for m in b.moves)
        total = sum(len(b.moves) for b in betas)
        if total == 0:
            return 0.2

        move_risk = avg_risk / total
        angle_risk = max(0, wall_angle_deg) / 90.0 * 0.3
        return min(1.0, move_risk * 0.7 + angle_risk * 0.3)

    def _default_difficulty(self) -> DifficultyAnalysis:
        return DifficultyAnalysis(
            grade_v_estimate=5,
            grade_font_estimate="6a+",
            crux_description="Unable to analyze — no holds detected",
            power_intensity=0.5,
            finger_intensity=0.5,
            core_intensity=0.5,
            coordination_intensity=0.5,
            balance_intensity=0.5,
            mobility_intensity=0.3,
            risk_level=0.2,
            flash_probability=0.3,
            send_probability=0.7,
            confidence=0.0,
        )

    def aggregate_stats(self, analyses: list[AnalysisResult]) -> dict:
        """Compute aggregate statistics across multiple analyses."""
        if not analyses:
            return {"count": 0}

        grades = [
            a.difficulty.grade_v_estimate
            for a in analyses
            if a.difficulty is not None
        ]

        return {
            "count": len(analyses),
            "average_grade_v": round(sum(grades) / len(grades), 1) if grades else None,
            "max_grade_v": max(grades) if grades else None,
            "min_grade_v": min(grades) if grades else None,
            "total_betas_generated": sum(len(a.betas) for a in analyses),
            "average_confidence": round(
                sum(a.vision_result.overall_confidence for a in analyses) / len(analyses), 3
            ),
        }
