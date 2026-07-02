from __future__ import annotations

from models.holds import DetectedHold
from models.routes import WallGeometry


class ConfidenceEstimator:
    """Computes and aggregates confidence scores across the vision pipeline."""

    # Minimum reasonable number of holds for a complete route
    MIN_HOLDS_FOR_ROUTE = 4

    def compute_overall_confidence(
        self,
        holds: list[DetectedHold],
        wall_detected: bool,
        wall_geometry: WallGeometry | None,
        image_quality: float,
    ) -> float:
        """Aggregate all signals into a single pipeline confidence score (0-1)."""
        scores: list[float] = []

        # Wall detection
        wall_score = 0.8 if wall_detected else 0.2
        if wall_geometry:
            wall_score = wall_geometry.confidence
        scores.append(wall_score * 0.25)

        # Hold detection quantity
        hold_count = len(holds)
        if hold_count == 0:
            hold_count_score = 0.0
        elif hold_count < self.MIN_HOLDS_FOR_ROUTE:
            hold_count_score = 0.3
        elif hold_count < 8:
            hold_count_score = 0.6
        else:
            hold_count_score = 0.9
        scores.append(hold_count_score * 0.25)

        # Average hold confidence
        if holds:
            avg_hold_conf = sum(h.confidence for h in holds) / len(holds)
        else:
            avg_hold_conf = 0.0
        scores.append(avg_hold_conf * 0.3)

        # Image quality
        scores.append(image_quality * 0.2)

        return round(sum(scores), 3)

    def compute_hold_confidence_adjustment(
        self,
        hold: DetectedHold,
        neighbors: list[DetectedHold],
    ) -> float:
        """Adjust hold confidence based on neighbor context.

        - Penalize holds with significantly overlapping polygons (likely duplicates)
        - Boost holds that cluster tightly with route peers
        """
        adjustment = 0.0

        # Check for overlap with neighbors
        bx1, by1, bw, bh = hold.bbox
        bx2, by2 = bx1 + bw, by1 + bh

        for other in neighbors:
            if other.id == hold.id:
                continue
            ox1, oy1, ow, oh = other.bbox
            ox2, oy2 = ox1 + ow, oy1 + oh

            inter_x1 = max(bx1, ox1)
            inter_y1 = max(by1, oy1)
            inter_x2 = min(bx2, ox2)
            inter_y2 = min(by2, oy2)

            if inter_x1 < inter_x2 and inter_y1 < inter_y2:
                inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
                hold_area = bw * bh
                if hold_area > 0:
                    overlap_ratio = inter_area / hold_area
                    adjustment -= overlap_ratio * 0.3  # penalize overlap

        # Cluster bonus: if same route_id as nearby holds
        same_route = [
            n for n in neighbors
            if n.route_id == hold.route_id and n.id != hold.id
        ]
        if same_route:
            adjustment += min(len(same_route) * 0.05, 0.2)

        adjusted = hold.confidence + adjustment
        return max(0.0, min(1.0, adjusted))

    def compute_breakdown(
        self,
        wall_detected: bool,
        wall_geometry: WallGeometry | None,
        holds: list[DetectedHold],
        image_quality: float,
        route_count: int,
    ) -> dict[str, float]:
        """Return named confidence scores for display in the UI."""
        hold_count = len(holds)
        avg_hold_conf = (
            sum(h.confidence for h in holds) / hold_count if holds else 0.0
        )

        return {
            "wall_detection": wall_geometry.confidence if wall_geometry else (0.8 if wall_detected else 0.0),
            "hold_detection": avg_hold_conf,
            "hold_count": min(hold_count / 15.0, 1.0),  # saturates at 15 holds
            "route_identification": min(0.4 + route_count * 0.3, 0.95) if route_count > 0 else 0.0,
            "image_quality": image_quality,
        }
