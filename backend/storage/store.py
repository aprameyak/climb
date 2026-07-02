from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from models.analysis import AnalysisResult
from models.climber import ClimberProfile


class FileStore:
    """JSON-file-based persistent storage for analyses and profiles."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.analyses_dir = base_dir / "analyses"
        self.profiles_dir = base_dir / "profiles"
        self.uploads_dir = base_dir / "uploads"

        for d in (self.analyses_dir, self.profiles_dir, self.uploads_dir):
            d.mkdir(parents=True, exist_ok=True)

    # ---- Analysis ----

    def save_analysis(self, result: AnalysisResult) -> str:
        """Persist an analysis result. Returns the analysis ID."""
        path = self.analyses_dir / f"{result.id}.json"
        path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return result.id

    def load_analysis(self, analysis_id: str) -> AnalysisResult | None:
        """Load a stored analysis result. Returns None if not found."""
        path = self.analyses_dir / f"{analysis_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return AnalysisResult.model_validate(data)
        except Exception:
            return None

    def list_analyses(self) -> list[AnalysisResult]:
        """Return all stored analyses, sorted newest first."""
        results: list[AnalysisResult] = []
        for path in sorted(self.analyses_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                results.append(AnalysisResult.model_validate(data))
            except Exception:
                continue
        return results

    def delete_analysis(self, analysis_id: str) -> bool:
        """Delete an analysis and its uploaded images. Returns True if deleted."""
        path = self.analyses_dir / f"{analysis_id}.json"
        if not path.exists():
            return False
        path.unlink()

        # Also delete associated uploads
        upload_dir = self.uploads_dir / analysis_id
        if upload_dir.exists():
            shutil.rmtree(upload_dir)

        return True

    # ---- Profile ----

    def save_profile(self, profile: ClimberProfile) -> str:
        """Persist a climber profile. Returns the profile ID."""
        path = self.profiles_dir / f"{profile.id}.json"
        path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
        return profile.id

    def load_profile(self, profile_id: str) -> ClimberProfile | None:
        """Load a climber profile. Returns None if not found."""
        path = self.profiles_dir / f"{profile_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ClimberProfile.model_validate(data)
        except Exception:
            return None

    def list_profiles(self) -> list[ClimberProfile]:
        """Return all stored climber profiles."""
        profiles: list[ClimberProfile] = []
        for path in sorted(self.profiles_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                profiles.append(ClimberProfile.model_validate(data))
            except Exception:
                continue
        return profiles

    def delete_profile(self, profile_id: str) -> bool:
        """Delete a climber profile. Returns True if deleted."""
        path = self.profiles_dir / f"{profile_id}.json"
        if not path.exists():
            return False
        path.unlink()
        return True

    # ---- Images ----

    def save_image(
        self,
        file_bytes: bytes,
        filename: str,
        analysis_id: str,
    ) -> Path:
        """Save an uploaded image to the uploads directory.

        Returns the path to the saved file.
        """
        upload_dir = self.uploads_dir / analysis_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename
        safe_name = Path(filename).name
        if not safe_name:
            safe_name = "image.jpg"

        target = upload_dir / safe_name

        # Handle duplicate filenames
        counter = 1
        while target.exists():
            stem = Path(safe_name).stem
            suffix = Path(safe_name).suffix
            target = upload_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        target.write_bytes(file_bytes)
        return target

    def get_upload_path(self, analysis_id: str, filename: str) -> Path | None:
        """Get the path to an uploaded file, or None if not found."""
        path = self.uploads_dir / analysis_id / filename
        return path if path.exists() else None
