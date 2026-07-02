from __future__ import annotations

import uuid
from collections import defaultdict

from models.holds import DetectedHold
from models.routes import BoardType, ClimbingRoute, WallGeometry


class RouteIdentifier:
    """Groups detected holds into routes and identifies the active route."""

    def identify_routes(
        self,
        holds: list[DetectedHold],
        wall_geometry: WallGeometry,
        board_type: BoardType = BoardType.UNKNOWN,
        image_paths: list[str] | None = None,
    ) -> list[ClimbingRoute]:
        """Group holds by route_id (color/tape) into ClimbingRoute objects.

        Returns list of candidate routes sorted by confidence (descending).
        """
        # Group by route_id
        by_route: dict[str | None, list[DetectedHold]] = defaultdict(list)
        for hold in holds:
            by_route[hold.route_id].append(hold)

        routes: list[ClimbingRoute] = []

        for route_color, route_holds in by_route.items():
            if not route_holds:
                continue

            start_holds = [h.id for h in route_holds if h.is_start]
            finish_holds = [h.id for h in route_holds if h.is_finish]

            # A valid route needs at least 3 holds
            if len(route_holds) < 2:
                continue

            # Confidence: routes with clear start/finish markers get higher confidence
            conf = 0.5
            if start_holds:
                conf += 0.2
            if finish_holds:
                conf += 0.2
            if len(route_holds) >= 5:
                conf += 0.1
            conf = min(conf, 0.95)

            # Average confidence of holds
            avg_hold_conf = sum(h.confidence for h in route_holds) / len(route_holds)
            conf = conf * 0.6 + avg_hold_conf * 0.4

            route = ClimbingRoute(
                id=f"route_{uuid.uuid4().hex[:8]}",
                name=f"{route_color.title() if route_color else 'Unknown'} Route",
                wall_geometry=wall_geometry,
                holds=route_holds,
                start_holds=start_holds,
                finish_holds=finish_holds,
                route_color=route_color,
                confidence=round(conf, 3),
                board_type=board_type,
                image_paths=image_paths or [],
            )
            routes.append(route)

        # Sort by confidence
        routes.sort(key=lambda r: r.confidence, reverse=True)
        return routes

    def select_active_route(
        self,
        routes: list[ClimbingRoute],
        board_type: BoardType = BoardType.UNKNOWN,
    ) -> ClimbingRoute | None:
        """Select the most likely active route from candidates.

        For known boards (MoonBoard, Kilter, Tension), we look for LED-lit holds.
        For gym walls, we pick the highest-confidence route that has start/finish markers.
        If all else fails, return the highest-confidence route overall.
        """
        if not routes:
            return None

        # Prefer routes that have both start AND finish markers
        complete = [r for r in routes if r.start_holds and r.finish_holds]
        if complete:
            return complete[0]

        # Prefer routes with at least a start marker
        started = [r for r in routes if r.start_holds]
        if started:
            return started[0]

        # Fall back to highest confidence
        return routes[0]

    def merge_route_holds(
        self,
        primary_holds: list[DetectedHold],
        secondary_holds: list[DetectedHold],
        iou_threshold: float = 0.3,
    ) -> list[DetectedHold]:
        """Merge holds from multiple images, deduplicating by IoU overlap.

        When processing multiple images of the same wall, this prevents
        duplicate hold detection.
        """
        merged = list(primary_holds)
        for new_hold in secondary_holds:
            if not self._has_overlap(new_hold, merged, iou_threshold):
                merged.append(new_hold)
        return merged

    def _has_overlap(
        self,
        hold: DetectedHold,
        existing: list[DetectedHold],
        iou_threshold: float,
    ) -> bool:
        """Check if hold overlaps significantly with any existing hold."""
        bx1, by1, bw, bh = hold.bbox
        bx2, by2 = bx1 + bw, by1 + bh

        for other in existing:
            ox1, oy1, ow, oh = other.bbox
            ox2, oy2 = ox1 + ow, oy1 + oh

            inter_x1 = max(bx1, ox1)
            inter_y1 = max(by1, oy1)
            inter_x2 = min(bx2, ox2)
            inter_y2 = min(by2, oy2)

            if inter_x1 >= inter_x2 or inter_y1 >= inter_y2:
                continue

            inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
            area_a = bw * bh
            area_b = ow * oh
            union_area = area_a + area_b - inter_area

            if union_area <= 0:
                continue

            iou = inter_area / union_area
            if iou >= iou_threshold:
                return True
        return False
