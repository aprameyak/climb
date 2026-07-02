from __future__ import annotations

from dataclasses import dataclass

from models.beta import BetaSolution, ClimbingMove, MoveType
from models.climber import ClimberProfile
from models.routes import ClimbingRoute


@dataclass
class BetaEvaluation:
    overall_score: float  # 0-1
    energy_score: float
    safety_score: float
    completeness_score: float  # does beta cover start-to-finish?
    crux_move_numbers: list[int]
    estimated_send_probability: float
    estimated_flash_probability: float
    warnings: list[str]


class BetaEvaluator:
    """Evaluates and scores complete beta solutions."""

    def evaluate_beta(
        self,
        beta: BetaSolution,
        profile: ClimberProfile,
        route: ClimbingRoute,
    ) -> BetaEvaluation:
        """Evaluate a complete beta solution.

        Args:
            beta: The beta solution to evaluate.
            profile: The climber this beta is for.
            route: The climbing route.

        Returns:
            BetaEvaluation with scores and recommendations.
        """
        warnings: list[str] = []

        energy_score = self.score_energy(beta)
        safety_score = self.score_safety(beta, profile, warnings)
        completeness_score = self.score_completeness(beta, route, warnings)
        crux_moves = self.compute_crux_moves(beta)
        send_prob = self.estimate_send_probability(beta, profile)
        flash_prob = self.estimate_flash_probability(beta, profile)

        overall = (
            energy_score * 0.2
            + safety_score * 0.3
            + completeness_score * 0.3
            + beta.overall_confidence * 0.2
        )

        return BetaEvaluation(
            overall_score=round(overall, 3),
            energy_score=round(energy_score, 3),
            safety_score=round(safety_score, 3),
            completeness_score=round(completeness_score, 3),
            crux_move_numbers=crux_moves,
            estimated_send_probability=round(send_prob, 3),
            estimated_flash_probability=round(flash_prob, 3),
            warnings=warnings,
        )

    def score_energy(self, beta: BetaSolution) -> float:
        """Score how energy-efficient this beta is (1.0 = perfectly efficient)."""
        if not beta.moves:
            return 0.5

        total_cost = sum(m.energy_cost for m in beta.moves)
        # Normalize: assume 10 moves at 0.5 cost = average baseline
        baseline = len(beta.moves) * 0.5
        if baseline == 0:
            return 0.5

        efficiency = 1.0 - (total_cost / baseline)
        return max(0.0, min(1.0, 0.5 + efficiency * 0.5))

    def score_safety(
        self,
        beta: BetaSolution,
        profile: ClimberProfile,
        warnings: list[str],
    ) -> float:
        """Score how safe this beta is for the given climber (1.0 = very safe)."""
        if not beta.moves:
            return 0.5

        safety_penalties = 0.0

        for move in beta.moves:
            # Penalize high-risk moves for beginners
            if move.risk_level > 0.4 and profile.indoor_grade_v < 5:
                safety_penalties += 0.2
                warnings.append(
                    f"Move {move.move_number} has high risk level ({move.risk_level:.0%}) "
                    "for climber's experience level"
                )

            # Penalize dynos for climbers with high fear of dynamic
            has_dyno = any(
                mt in (MoveType.FULL_DYNO, MoveType.CONTROLLED_DYNO)
                for mt in move.move_types
            )
            if has_dyno and profile.fear_of_dynamic > 0.6:
                safety_penalties += 0.15
                warnings.append(
                    f"Move {move.move_number} includes dynamic movement "
                    "— climber profile indicates high fear of dynamics"
                )

        avg_penalty = safety_penalties / max(len(beta.moves), 1)
        return max(0.0, min(1.0, 1.0 - avg_penalty))

    def score_completeness(
        self,
        beta: BetaSolution,
        route: ClimbingRoute,
        warnings: list[str],
    ) -> float:
        """Score whether the beta covers the complete route from start to finish."""
        if not beta.moves:
            warnings.append("Beta has no moves")
            return 0.0

        # Check that start holds are in the first move
        if route.start_holds and beta.moves:
            first_move = beta.moves[0]
            used_holds = set()
            for limb_pos in [
                first_move.body_position.left_hand,
                first_move.body_position.right_hand,
                first_move.body_position.left_foot,
                first_move.body_position.right_foot,
            ]:
                if limb_pos.hold_id:
                    used_holds.add(limb_pos.hold_id)

        # Check that finish holds are in the last move
        if route.finish_holds and beta.moves:
            last_move = beta.moves[-1]
            used_holds = set()
            for limb_pos in [
                last_move.body_position.left_hand,
                last_move.body_position.right_hand,
            ]:
                if limb_pos.hold_id:
                    used_holds.add(limb_pos.hold_id)

            if not any(fh in used_holds for fh in route.finish_holds):
                warnings.append("Beta may not reach the finish hold")
                return 0.6

        # Penalty for very short betas (possibly incomplete)
        if len(beta.moves) < 3 and len(route.holds) > 5:
            warnings.append("Beta appears short relative to route length — may be incomplete")
            return 0.6

        return 1.0

    def compute_crux_moves(self, beta: BetaSolution) -> list[int]:
        """Identify crux moves (top 20% by difficulty)."""
        if not beta.moves:
            return []

        difficulties = [(m.move_number, m.difficulty_rating) for m in beta.moves]
        difficulties.sort(key=lambda x: x[1], reverse=True)
        threshold = 0.7  # difficulty threshold for crux
        crux = [num for num, diff in difficulties if diff >= threshold]

        # Minimum: if any move is significantly harder than average, mark it
        if not crux and difficulties:
            avg_diff = sum(d for _, d in difficulties) / len(difficulties)
            crux = [num for num, diff in difficulties if diff > avg_diff * 1.4]

        return crux[:3]  # max 3 crux moves

    def estimate_send_probability(
        self, beta: BetaSolution, profile: ClimberProfile
    ) -> float:
        """Estimate probability of eventually sending the route with this beta."""
        if not beta.moves:
            return 0.3

        # Base probability from beta confidence
        base = beta.overall_confidence * 0.8

        # Adjust for crux moves relative to climber grade
        crux_moves = [m for m in beta.moves if m.is_crux]
        if crux_moves:
            avg_crux_difficulty = sum(m.difficulty_rating for m in crux_moves) / len(crux_moves)
            # If crux difficulty exceeds climber's level, reduce send probability
            grade_ratio = profile.indoor_grade_v / 17.0
            difficulty_gap = avg_crux_difficulty - grade_ratio
            base -= max(0, difficulty_gap * 0.5)

        # Adjust for energy efficiency
        base += (1.0 - beta.total_energy_cost) * 0.1

        return max(0.05, min(0.98, base))

    def estimate_flash_probability(
        self, beta: BetaSolution, profile: ClimberProfile
    ) -> float:
        """Estimate probability of flashing (sending first try) with this beta."""
        send_prob = self.estimate_send_probability(beta, profile)
        # Flash is roughly 1/3 of send probability for typical climbers
        flash_factor = 0.25 + profile.dynamic_comfort_score * 0.1
        return round(send_prob * flash_factor, 3)
