from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

import anthropic

from models.routes import WallAngle, WallGeometry, WALL_ANGLE_DEGREES


@dataclass
class WallDetectionResult:
    wall_detected: bool
    wall_geometry: Optional[WallGeometry]
    wall_bounds: list[tuple[float, float]] = field(default_factory=list)
    confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)


_WALL_DETECTOR_SYSTEM = """You are a computer vision system specialized in detecting indoor climbing walls.

Analyze the provided image and return a JSON object with the following structure:

{
  "wall_detected": boolean,
  "wall_angle_degrees": number,  // degrees from vertical: negative=slab, 0=vertical, positive=overhang, 90=roof
  "wall_type": string,  // one of: slab_70, slab_80, vertical, overhang_5, overhang_10, overhang_15, overhang_20, overhang_25, overhang_30, overhang_35, overhang_40, overhang_45, roof
  "height_m": number,  // estimated wall height in meters
  "width_m": number,   // estimated wall width in meters
  "has_volumes": boolean,
  "wall_bounds": [[x1,y1],[x2,y2],[x3,y3],[x4,y4]],  // normalized 0-1 corner points of wall area
  "confidence": number,  // 0.0-1.0
  "reasoning": string,
  "warnings": [string]  // non-fatal issues
}

Rules:
- Coordinates must be normalized 0-1 where (0,0) is top-left
- If no climbing wall is detected, set wall_detected=false and explain in warnings
- Be conservative with confidence — prefer 0.5 over 0.9 when uncertain
- wall_angle_degrees: most gym walls are between -20 (slab) and +45 (steep overhang)
- If you see volumes (large 3D shapes bolted to wall), set has_volumes=true
- Only return valid JSON — no markdown fences, no explanation outside the JSON
"""


def _angle_to_wall_type(degrees: float) -> WallAngle:
    """Map angle in degrees to the closest WallAngle enum value."""
    thresholds = [
        (-25, WallAngle.SLAB_70),
        (-15, WallAngle.SLAB_80),
        (2.5, WallAngle.VERTICAL),
        (7.5, WallAngle.OVERHANG_5),
        (12.5, WallAngle.OVERHANG_10),
        (17.5, WallAngle.OVERHANG_15),
        (22.5, WallAngle.OVERHANG_20),
        (27.5, WallAngle.OVERHANG_25),
        (32.5, WallAngle.OVERHANG_30),
        (37.5, WallAngle.OVERHANG_35),
        (42.5, WallAngle.OVERHANG_40),
        (67.5, WallAngle.OVERHANG_45),
    ]
    for threshold, wall_type in thresholds:
        if degrees <= threshold:
            return wall_type
    return WallAngle.ROOF


class WallDetector:
    """Detects climbing wall geometry using Claude Vision."""

    def __init__(self, anthropic_client: anthropic.Anthropic) -> None:
        self.client = anthropic_client

    def detect(self, image_b64: str) -> WallDetectionResult:
        """Detect wall in image.

        Args:
            image_b64: Base64-encoded JPEG image string.

        Returns:
            WallDetectionResult with geometry and confidence.
        """
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=_WALL_DETECTOR_SYSTEM,
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
                            {
                                "type": "text",
                                "text": "Analyze this climbing wall image and return the JSON response.",
                            },
                        ],
                    }
                ],
            )
            raw = message.content[0].text
            data = self._parse_json(raw)
            return self._build_result(data)
        except Exception as exc:
            return WallDetectionResult(
                wall_detected=False,
                wall_geometry=None,
                confidence=0.0,
                warnings=[f"Wall detection failed: {exc!s}"],
            )

    def _parse_json(self, text: str) -> dict:
        # Strip markdown code fences if present
        text = re.sub(r"```(?:json)?", "", text).strip()
        return json.loads(text)

    def _build_result(self, data: dict) -> WallDetectionResult:
        if not data.get("wall_detected", False):
            return WallDetectionResult(
                wall_detected=False,
                wall_geometry=None,
                confidence=data.get("confidence", 0.0),
                warnings=data.get("warnings", ["No climbing wall detected in image."]),
            )

        angle = float(data.get("wall_angle_degrees", 0.0))
        wall_type = _angle_to_wall_type(angle)

        geometry = WallGeometry(
            angle_degrees=angle,
            wall_type=wall_type,
            height_m=float(data.get("height_m", 4.0)),
            width_m=float(data.get("width_m", 3.0)),
            has_volumes=bool(data.get("has_volumes", False)),
            confidence=float(data.get("confidence", 0.5)),
        )

        bounds_raw = data.get("wall_bounds", [])
        bounds: list[tuple[float, float]] = []
        for point in bounds_raw:
            if isinstance(point, (list, tuple)) and len(point) == 2:
                x = max(0.0, min(1.0, float(point[0])))
                y = max(0.0, min(1.0, float(point[1])))
                bounds.append((x, y))

        return WallDetectionResult(
            wall_detected=True,
            wall_geometry=geometry,
            wall_bounds=bounds,
            confidence=float(data.get("confidence", 0.5)),
            warnings=data.get("warnings", []),
        )
