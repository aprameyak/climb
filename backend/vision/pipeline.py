from __future__ import annotations

import time
from pathlib import Path

import anthropic

from models.analysis import VisionPipelineResult
from models.routes import BoardType, WallGeometry

from .confidence import ConfidenceEstimator
from .hold_detector import HoldDetector
from .preprocessor import ImagePreprocessor
from .route_identifier import RouteIdentifier
from .wall_detector import WallDetector


class VisionPipeline:
    """Orchestrates the full computer vision pipeline for climbing wall analysis.

    Pipeline steps:
    1. Load and preprocess each image
    2. Detect wall geometry in the best-quality image
    3. Detect all holds using Claude Vision
    4. Merge holds from multiple images (deduplicate)
    5. Identify routes from hold groups
    6. Compute confidence scores
    7. Return VisionPipelineResult
    """

    def __init__(self, anthropic_client: anthropic.Anthropic) -> None:
        self.client = anthropic_client
        self.preprocessor = ImagePreprocessor()
        self.wall_detector = WallDetector(anthropic_client)
        self.hold_detector = HoldDetector(anthropic_client)
        self.route_identifier = RouteIdentifier()
        self.confidence_estimator = ConfidenceEstimator()

    async def process_images(
        self,
        image_paths: list[Path],
        board_type: BoardType = BoardType.UNKNOWN,
    ) -> VisionPipelineResult:
        """Run the complete pipeline on one or more images.

        Args:
            image_paths: List of paths to climbing wall images.
            board_type: Known board type if applicable.

        Returns:
            VisionPipelineResult with all detections and confidence scores.
        """
        start_time = time.perf_counter()
        warnings: list[str] = []
        all_holds = []

        if not image_paths:
            return self._empty_result("", start_time, ["No images provided."])

        # --- Step 1: Load and assess image quality ---
        images_with_quality: list[tuple[Path, object, str, int, int, float]] = []
        for path in image_paths:
            try:
                img, b64, w, h = self.preprocessor.prepare_for_api(path)
                quality_metrics = self.preprocessor.estimate_quality(img)
                quality_score = quality_metrics.overall_quality()
                warnings.extend(quality_metrics.warnings())
                images_with_quality.append((path, img, b64, w, h, quality_score))
            except Exception as exc:
                warnings.append(f"Failed to load image {path.name}: {exc!s}")

        if not images_with_quality:
            return self._empty_result(
                str(image_paths[0]), start_time, warnings + ["All images failed to load."]
            )

        # Sort by quality score; use best image for wall detection
        images_with_quality.sort(key=lambda x: x[5], reverse=True)
        best_path, best_img, best_b64, best_w, best_h, best_quality = images_with_quality[0]

        # --- Step 2: Detect wall geometry ---
        wall_result = self.wall_detector.detect(best_b64)
        warnings.extend(wall_result.warnings)

        wall_geometry = wall_result.wall_geometry
        if not wall_result.wall_detected or wall_geometry is None:
            warnings.append(
                "No climbing wall detected. Results may be inaccurate. "
                "Ensure the image shows a clear view of the climbing wall."
            )
            wall_geometry = WallGeometry(angle_degrees=0.0)

        # --- Step 3: Detect holds in each image ---
        for path, img, b64, w, h, quality in images_with_quality:
            holds, hold_warnings = self.hold_detector.detect_holds(b64, wall_geometry, w, h)
            warnings.extend(hold_warnings)

            if path == best_path:
                all_holds = holds
            else:
                # Merge holds from additional images
                all_holds = self.route_identifier.merge_route_holds(all_holds, holds)

        # --- Step 4: Apply confidence adjustments based on context ---
        for hold in all_holds:
            adjusted = self.confidence_estimator.compute_hold_confidence_adjustment(
                hold, all_holds
            )
            # Update confidence (we need to create a new hold since model is immutable)
            # Using object.__setattr__ to bypass pydantic protection in this pipeline context
            object.__setattr__(hold, "confidence", adjusted)

        # --- Step 5: Identify routes ---
        route_candidates = self.route_identifier.identify_routes(
            all_holds,
            wall_geometry,
            board_type,
            [str(p) for p in image_paths],
        )
        active_route = self.route_identifier.select_active_route(route_candidates, board_type)

        # --- Step 6: Compute confidence ---
        overall_confidence = self.confidence_estimator.compute_overall_confidence(
            all_holds, wall_result.wall_detected, wall_geometry, best_quality
        )
        confidence_breakdown = self.confidence_estimator.compute_breakdown(
            wall_result.wall_detected,
            wall_geometry,
            all_holds,
            best_quality,
            len(route_candidates),
        )

        # Warn if low confidence
        if overall_confidence < 0.7:
            warnings.append(
                f"Overall confidence is {overall_confidence:.0%}. "
                "Consider providing additional images from different angles."
            )

        requires_additional = (
            overall_confidence < 0.6
            or len(all_holds) < 4
            or not route_candidates
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return VisionPipelineResult(
            image_path=str(best_path),
            wall_detected=wall_result.wall_detected,
            wall_geometry=wall_geometry,
            holds=all_holds,
            route_candidates=route_candidates,
            active_route=active_route,
            processing_time_ms=round(elapsed_ms, 1),
            overall_confidence=overall_confidence,
            warnings=warnings,
            requires_additional_images=requires_additional,
            confidence_breakdown=confidence_breakdown,
            image_quality={
                "best_image_quality": round(best_quality, 3),
                "num_images_processed": len(images_with_quality),
            },
        )

    def _empty_result(
        self, image_path: str, start_time: float, warnings: list[str]
    ) -> VisionPipelineResult:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return VisionPipelineResult(
            image_path=image_path,
            wall_detected=False,
            wall_geometry=None,
            holds=[],
            route_candidates=[],
            active_route=None,
            processing_time_ms=round(elapsed_ms, 1),
            overall_confidence=0.0,
            warnings=warnings,
            requires_additional_images=True,
            confidence_breakdown={},
        )
