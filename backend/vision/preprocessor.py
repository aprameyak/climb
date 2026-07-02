from __future__ import annotations

import base64
import io
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ExifTags


class ImageQualityMetrics:
    blur_score: float  # Higher = sharper (Laplacian variance)
    exposure_score: float  # 0=underexposed, 0.5=ideal, 1=overexposed
    noise_score: float  # 0=clean, 1=very noisy

    def __init__(self, blur: float, exposure: float, noise: float) -> None:
        self.blur_score = blur
        self.exposure_score = exposure
        self.noise_score = noise

    def overall_quality(self) -> float:
        """0-1 quality estimate. Higher = better for CV processing."""
        blur_ok = min(self.blur_score / 200.0, 1.0)  # 200+ variance = sharp
        exposure_ok = 1.0 - abs(self.exposure_score - 0.5) * 2.0  # penalty away from 0.5
        noise_ok = 1.0 - self.noise_score
        return (blur_ok * 0.5 + exposure_ok * 0.3 + noise_ok * 0.2)

    def warnings(self) -> list[str]:
        issues: list[str] = []
        if self.blur_score < 50:
            issues.append("Image appears blurry — hold detection may be less accurate.")
        if self.exposure_score < 0.15:
            issues.append("Image appears underexposed — dark areas may contain missed holds.")
        if self.exposure_score > 0.85:
            issues.append("Image appears overexposed — bright areas may wash out hold details.")
        if self.noise_score > 0.6:
            issues.append("High image noise detected — confidence scores may be reduced.")
        return issues


class ImagePreprocessor:
    """Handles all image loading, correction, and quality assessment."""

    MAX_DIM = 2048

    def load_image(self, path: Path) -> np.ndarray:
        """Load image using Pillow (handles wide format support) and convert to OpenCV BGR."""
        pil_img = Image.open(path).convert("RGB")
        pil_img = self._auto_rotate_pil(pil_img)
        img = np.array(pil_img)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        return img

    def _auto_rotate_pil(self, img: Image.Image) -> Image.Image:
        """Use EXIF orientation to auto-rotate image."""
        try:
            exif = img._getexif()  # type: ignore[attr-defined]
            if exif is None:
                return img
            orientation_key = next(
                k for k, v in ExifTags.TAGS.items() if v == "Orientation"
            )
            orientation = exif.get(orientation_key)
            rotations = {3: 180, 6: 270, 8: 90}
            if orientation in rotations:
                img = img.rotate(rotations[orientation], expand=True)
        except Exception:
            pass
        return img

    def resize_if_needed(self, img: np.ndarray, max_dim: int = MAX_DIM) -> np.ndarray:
        """Resize image so largest dimension <= max_dim, preserving aspect ratio."""
        h, w = img.shape[:2]
        largest = max(h, w)
        if largest <= max_dim:
            return img
        scale = max_dim / largest
        new_w = int(w * scale)
        new_h = int(h * scale)
        return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    def estimate_quality(self, img: np.ndarray) -> ImageQualityMetrics:
        """Estimate image quality metrics for pre-processing warnings."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Blur: Laplacian variance (higher = sharper)
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        # Exposure: mean luminance 0-1
        exposure_score = float(gray.mean()) / 255.0

        # Noise: estimate via high-frequency noise in uniform regions
        # Use a simple proxy: normalized std of Laplacian residuals
        lap = cv2.Laplacian(gray.astype(np.float32), cv2.CV_32F)
        noise_score = float(np.std(lap)) / (blur_score + 1e-6)
        noise_score = min(noise_score / 10.0, 1.0)  # normalize

        return ImageQualityMetrics(blur_score, exposure_score, noise_score)

    def to_base64(self, img: np.ndarray) -> str:
        """Convert OpenCV BGR image to base64-encoded JPEG string (for Claude API)."""
        # Convert to RGB for PIL
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        buffer = io.BytesIO()
        pil_img.save(buffer, format="JPEG", quality=90)
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("utf-8")

    def prepare_for_api(self, path: Path) -> tuple[np.ndarray, str, int, int]:
        """Full pipeline: load -> resize -> quality check -> base64.

        Returns (img_array, base64_string, width, height).
        """
        img = self.load_image(path)
        img = self.resize_if_needed(img)
        b64 = self.to_base64(img)
        h, w = img.shape[:2]
        return img, b64, w, h

    def correct_fisheye(
        self, img: np.ndarray, k1: float = 0.0, k2: float = 0.0
    ) -> np.ndarray:
        """Apply radial distortion correction for fisheye/ultrawide lenses.

        k1, k2: radial distortion coefficients. These should be calibrated
        from the specific camera. Without calibration, this is a no-op.
        If you have camera calibration data, pass the coefficients here.
        """
        if abs(k1) < 1e-6 and abs(k2) < 1e-6:
            return img  # No correction needed
        h, w = img.shape[:2]
        cx, cy = w / 2.0, h / 2.0
        # Approximate focal length assuming 70 degree FOV
        f = w / (2.0 * math.tan(math.radians(35)))
        camera_matrix = np.array([[f, 0, cx], [0, f, cy], [0, 0, 1]], dtype=np.float64)
        dist_coeffs = np.array([k1, k2, 0, 0, 0], dtype=np.float64)
        undistorted = cv2.undistort(img, camera_matrix, dist_coeffs)
        return undistorted

    def enhance_contrast(self, img: np.ndarray) -> np.ndarray:
        """Apply CLAHE contrast enhancement to improve hold visibility in dark images."""
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l_channel)
        enhanced_lab = cv2.merge([l_enhanced, a, b])
        return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
