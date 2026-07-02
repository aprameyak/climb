from __future__ import annotations

import json
import math
import re
import uuid
from typing import Any, Optional

import anthropic

from models.holds import (
    DetectedHold,
    GripDirection,
    HoldPosition,
    HoldType,
    HoldUsability,
    RouteMarkerType,
    SurfaceNormal,
    HOLD_TYPE_DEPTH_CM,
    HOLD_TYPE_FRICTION,
)
from models.routes import WallGeometry


_HOLD_DETECTOR_SYSTEM = """You are a world-class climbing hold detection system. Your task is to identify every climbing hold visible in the image and return precise, structured data.

Return ONLY a JSON object with this exact structure:
{
  "holds": [
    {
      "id": "h1",
      "center": {"x": 0.45, "y": 0.32},
      "polygon": [[0.42, 0.29], [0.48, 0.29], [0.49, 0.35], [0.41, 0.35]],
      "hold_type": "crimp",
      "grip_direction": "pull_down",
      "orientation_degrees": 0,
      "is_start": false,
      "is_finish": false,
      "route_id": "yellow",
      "confidence": 0.87,
      "color_description": "yellow resin hold",
      "color_rgb": [230, 200, 30],
      "usability": {
        "left_hand": true,
        "right_hand": true,
        "left_foot": true,
        "right_foot": true
      },
      "limb_quality": {
        "lh": 0.7,
        "rh": 0.7,
        "lf": 0.4,
        "rf": 0.4
      }
    }
  ],
  "warnings": ["string"],
  "multiple_routes_detected": boolean,
  "route_colors_detected": ["yellow", "blue"]
}

CRITICAL RULES:
1. ALL coordinates must be normalized 0.0 to 1.0 where (0,0) is TOP-LEFT
2. x increases left-to-right, y increases top-to-bottom
3. Polygon must have 4-8 points forming the actual hold boundary
4. center must be inside the polygon
5. confidence: 0.9+ only for clearly visible holds, 0.5-0.7 for partially hidden/uncertain
6. Do NOT detect wall features, bolt holes, or shadows as holds
7. is_start: true only for holds with green tape or marked 'START'
8. is_finish: true only for holds with red tape, marked 'TOP', or clearly the highest target hold
9. route_id: use the tape/LED color as the route identifier (e.g. "yellow", "blue", "red")
10. If multiple routes share a similar color, describe them distinctly
11. Detect EVERY hold — do not skip small footholds
12. For volumes: polygon should approximate the entire volume shape
13. hold_type options: jug, positive_edge, incut, flat_edge, crimp, micro_crimp, pocket, mono, pocket_2f, pocket_3f, sloper, pinch, rail, horn, sidepull, undercling, gaston, volume, screw_on, chip, foot_chip, smear, macro, dual_texture, unknown
14. grip_direction options: pull_down, pull_left, pull_right, undercling, pinch, compress, slap, palm
15. orientation_degrees: 0=top, 90=right, 180=bottom, 270=left
16. Only return valid JSON — no markdown, no explanations outside JSON
"""


class HoldDetector:
    """Detects climbing holds using Claude Vision AI."""

    def __init__(self, anthropic_client: anthropic.Anthropic) -> None:
        self.client = anthropic_client

    def detect_holds(
        self,
        image_b64: str,
        wall_geometry: WallGeometry,
        image_width: int,
        image_height: int,
    ) -> tuple[list[DetectedHold], list[str]]:
        """Detect all holds in the image using Claude Vision.

        Args:
            image_b64: Base64-encoded JPEG.
            wall_geometry: Detected wall geometry for context.
            image_width: Image width in pixels.
            image_height: Image height in pixels.

        Returns:
            (holds, warnings)
        """
        user_prompt = self._build_user_prompt(wall_geometry, image_width, image_height)

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=8096,
                system=_HOLD_DETECTOR_SYSTEM,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_b64,
                                },
                            },
                            {"type": "text", "text": user_prompt},
                        ],
                    }
                ],
            )

            raw = message.content[0].text
            data = self._parse_json(raw)
            holds, parse_warnings = self._parse_holds(data, wall_geometry)
            api_warnings = data.get("warnings", [])
            return holds, api_warnings + parse_warnings

        except Exception as exc:
            return [], [f"Hold detection failed: {exc!s}"]

    def _build_user_prompt(
        self, geometry: WallGeometry, width: int, height: int
    ) -> str:
        return (
            f"Detect all climbing holds in this image.\n\n"
            f"Wall context:\n"
            f"- Wall angle: {geometry.angle_degrees:.1f}° from vertical "
            f"({'slab' if geometry.angle_degrees < 0 else 'overhang' if geometry.angle_degrees > 2 else 'vertical'})\n"
            f"- Wall size: ~{geometry.width_m:.1f}m wide × {geometry.height_m:.1f}m tall\n"
            f"- Has volumes: {geometry.has_volumes}\n"
            f"- Image dimensions: {width}×{height} pixels\n\n"
            f"Return the complete JSON object with every hold. "
            f"Be thorough — missing holds creates unsafe beta."
        )

    def _parse_json(self, text: str) -> dict[str, Any]:
        text = re.sub(r"```(?:json)?", "", text).strip()
        # Sometimes the model adds trailing comma before closing bracket
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*]", "]", text)
        return json.loads(text)

    def _parse_holds(
        self, data: dict[str, Any], wall_geometry: WallGeometry
    ) -> tuple[list[DetectedHold], list[str]]:
        holds: list[DetectedHold] = []
        warnings: list[str] = []
        raw_holds = data.get("holds", [])

        for i, raw in enumerate(raw_holds):
            try:
                hold = self._parse_single_hold(raw, wall_geometry, index=i)
                holds.append(hold)
            except Exception as exc:
                warnings.append(f"Skipped hold #{i}: {exc!s}")

        if not holds:
            warnings.append("No valid holds could be parsed from detection response.")

        return holds, warnings

    def _parse_single_hold(
        self, raw: dict[str, Any], wall_geometry: WallGeometry, index: int
    ) -> DetectedHold:
        # Center
        center_raw = raw.get("center", {})
        center = HoldPosition(
            x=float(center_raw.get("x", 0.5)),
            y=float(center_raw.get("y", 0.5)),
            z_estimate=0.0,
        )

        # Polygon
        polygon_raw = raw.get("polygon", [])
        polygon: list[tuple[float, float]] = []
        for pt in polygon_raw:
            if isinstance(pt, (list, tuple)) and len(pt) == 2:
                x = max(0.0, min(1.0, float(pt[0])))
                y = max(0.0, min(1.0, float(pt[1])))
                polygon.append((x, y))
        if len(polygon) < 3:
            # Fall back to a bounding box from center
            cx, cy = center.x, center.y
            size = 0.03
            polygon = [
                (cx - size, cy - size),
                (cx + size, cy - size),
                (cx + size, cy + size),
                (cx - size, cy + size),
            ]

        # Bounding box from polygon
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        bbox = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

        # Hold type
        hold_type_str = raw.get("hold_type", "unknown").lower().replace("-", "_").replace(" ", "_")
        try:
            hold_type = HoldType(hold_type_str)
        except ValueError:
            hold_type = HoldType.UNKNOWN

        # Grip direction
        grip_str = raw.get("grip_direction", "pull_down").lower().replace("-", "_").replace(" ", "_")
        try:
            grip_direction = GripDirection(grip_str)
        except ValueError:
            grip_direction = GripDirection.PULL_DOWN

        # Infer grip direction from hold type if not specified
        if grip_direction == GripDirection.PULL_DOWN:
            grip_direction = self._infer_grip_direction(hold_type, float(raw.get("orientation_degrees", 0)))

        # Surface normal from orientation and wall angle
        orientation = float(raw.get("orientation_degrees", 0))
        surface_normal = self._compute_surface_normal(orientation, wall_geometry.angle_degrees)

        # Usability
        usability_raw = raw.get("usability", {})
        quality_raw = raw.get("limb_quality", {})
        usability = HoldUsability(
            left_hand=bool(usability_raw.get("left_hand", True)),
            right_hand=bool(usability_raw.get("right_hand", True)),
            left_foot=bool(usability_raw.get("left_foot", True)),
            right_foot=bool(usability_raw.get("right_foot", True)),
            quality_lh=float(quality_raw.get("lh", 0.5)),
            quality_rh=float(quality_raw.get("rh", 0.5)),
            quality_lf=float(quality_raw.get("lf", 0.3)),
            quality_rf=float(quality_raw.get("rf", 0.3)),
        )

        # Marker type
        is_start = bool(raw.get("is_start", False))
        is_finish = bool(raw.get("is_finish", False))
        if is_start:
            marker_type = RouteMarkerType.START
        elif is_finish:
            marker_type = RouteMarkerType.FINISH
        else:
            marker_type = RouteMarkerType.NONE

        # Color
        color_rgb_raw = raw.get("color_rgb")
        color_rgb: Optional[tuple[int, int, int]] = None
        if isinstance(color_rgb_raw, (list, tuple)) and len(color_rgb_raw) == 3:
            color_rgb = (int(color_rgb_raw[0]), int(color_rgb_raw[1]), int(color_rgb_raw[2]))

        # Generate usable hand/foot positions from polygon centroid + small offsets
        usable_hand_positions = self._generate_hand_positions(center, hold_type)
        usable_foot_positions = self._generate_foot_positions(center, hold_type)

        return DetectedHold(
            id=raw.get("id") or f"hold_{index}_{uuid.uuid4().hex[:6]}",
            polygon=polygon,
            center=center,
            orientation_degrees=orientation,
            estimated_depth_cm=HOLD_TYPE_DEPTH_CM.get(hold_type, 2.0),
            surface_normal=surface_normal,
            hold_type=hold_type,
            grip_direction=grip_direction,
            estimated_difficulty=float(raw.get("difficulty", 5.0)),
            estimated_friction=HOLD_TYPE_FRICTION.get(hold_type, 0.6),
            usability=usability,
            usable_hand_positions=usable_hand_positions,
            usable_foot_positions=usable_foot_positions,
            confidence=max(0.0, min(1.0, float(raw.get("confidence", 0.5)))),
            bbox=bbox,
            color_rgb=color_rgb,
            is_start=is_start,
            is_finish=is_finish,
            route_id=raw.get("route_id"),
            marker_type=marker_type,
        )

    def _infer_grip_direction(self, hold_type: HoldType, orientation: float) -> GripDirection:
        """Infer likely grip direction from hold type and orientation."""
        if hold_type == HoldType.UNDERCLING:
            return GripDirection.UNDERCLING
        if hold_type == HoldType.GASTON:
            return GripDirection.PULL_LEFT if orientation < 180 else GripDirection.PULL_RIGHT
        if hold_type in (HoldType.SIDEPULL,):
            return GripDirection.PULL_LEFT if orientation < 180 else GripDirection.PULL_RIGHT
        if hold_type in (HoldType.PINCH,):
            return GripDirection.PINCH
        if hold_type == HoldType.SLOPER:
            return GripDirection.PALM
        if hold_type == HoldType.VOLUME:
            return GripDirection.COMPRESS
        return GripDirection.PULL_DOWN

    def _compute_surface_normal(self, orientation_deg: float, wall_angle_deg: float) -> SurfaceNormal:
        """Estimate surface normal from hold orientation and wall angle."""
        # Z-component: how much the hold faces the climber
        # On a vertical wall (0°), holds face straight out (dz=1)
        # On a roof (90°), holds face down (dy=1, dz≈0)
        import math
        wall_rad = math.radians(wall_angle_deg)
        dz = math.cos(wall_rad)
        dy_base = math.sin(wall_rad)  # positive = angled upward on overhang

        # Orientation rotates the hold in the wall plane
        orient_rad = math.radians(orientation_deg)
        dx = math.sin(orient_rad) * 0.3  # small lateral component
        dy = dy_base + math.cos(orient_rad) * 0.1

        magnitude = math.sqrt(dx**2 + dy**2 + dz**2)
        if magnitude < 1e-6:
            return SurfaceNormal(dx=0.0, dy=0.0, dz=1.0)
        return SurfaceNormal(dx=dx / magnitude, dy=dy / magnitude, dz=dz / magnitude)

    def _generate_hand_positions(
        self, center: HoldPosition, hold_type: HoldType
    ) -> list[HoldPosition]:
        """Generate likely hand grip positions based on hold type."""
        if hold_type in (HoldType.JUG, HoldType.HORN, HoldType.MACRO):
            # Multiple grip positions possible
            return [
                HoldPosition(x=max(0, center.x - 0.01), y=center.y, z_estimate=0.0),
                HoldPosition(x=center.x, y=center.y, z_estimate=0.0),
                HoldPosition(x=min(1, center.x + 0.01), y=center.y, z_estimate=0.0),
            ]
        if hold_type == HoldType.RAIL:
            return [
                HoldPosition(x=max(0, center.x - 0.02), y=center.y, z_estimate=0.0),
                HoldPosition(x=center.x, y=center.y, z_estimate=0.0),
                HoldPosition(x=min(1, center.x + 0.02), y=center.y, z_estimate=0.0),
            ]
        # Default: single grip position at center
        return [HoldPosition(x=center.x, y=center.y, z_estimate=0.0)]

    def _generate_foot_positions(
        self, center: HoldPosition, hold_type: HoldType
    ) -> list[HoldPosition]:
        """Generate foot smear/edge positions based on hold type."""
        if hold_type in (HoldType.VOLUME, HoldType.MACRO):
            # Larger surface — multiple foot positions
            return [
                HoldPosition(x=max(0, center.x - 0.015), y=min(1, center.y + 0.01), z_estimate=0.0),
                HoldPosition(x=center.x, y=min(1, center.y + 0.01), z_estimate=0.0),
                HoldPosition(x=min(1, center.x + 0.015), y=min(1, center.y + 0.01), z_estimate=0.0),
            ]
        if hold_type in (HoldType.FOOT_CHIP, HoldType.CHIP, HoldType.SMEAR):
            return [HoldPosition(x=center.x, y=min(1, center.y + 0.005), z_estimate=0.0)]
        # Standard hold: foot can edge on top
        return [HoldPosition(x=center.x, y=min(1, center.y + 0.008), z_estimate=0.0)]
