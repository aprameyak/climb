from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from config import Settings, get_settings
from models.climber import ClimberProfile
from storage.store import FileStore

router = APIRouter(prefix="/api/v1/profiles", tags=["profiles"])


def get_store(settings: Annotated[Settings, Depends(get_settings)]) -> FileStore:
    return FileStore(settings.storage_dir)


@router.get("/", response_model=list[ClimberProfile])
async def list_profiles(store: Annotated[FileStore, Depends(get_store)]) -> list[ClimberProfile]:
    return store.list_profiles()


@router.post("/", response_model=ClimberProfile, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile: ClimberProfile,
    store: Annotated[FileStore, Depends(get_store)],
) -> ClimberProfile:
    if not profile.id:
        profile = profile.model_copy(update={"id": f"profile_{uuid.uuid4().hex[:8]}"})
    store.save_profile(profile)
    return profile


@router.get("/{profile_id}", response_model=ClimberProfile)
async def get_profile(
    profile_id: str,
    store: Annotated[FileStore, Depends(get_store)],
) -> ClimberProfile:
    profile = store.load_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")
    return profile


@router.put("/{profile_id}", response_model=ClimberProfile)
async def update_profile(
    profile_id: str,
    updated: ClimberProfile,
    store: Annotated[FileStore, Depends(get_store)],
) -> ClimberProfile:
    existing = store.load_profile(profile_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")

    # Ensure ID stays consistent
    merged = updated.model_copy(update={"id": profile_id})
    store.save_profile(merged)
    return merged


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: str,
    store: Annotated[FileStore, Depends(get_store)],
) -> None:
    if not store.delete_profile(profile_id):
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found")


@router.get("/default/profile", response_model=ClimberProfile)
async def get_default_profile() -> ClimberProfile:
    """Return the default climber profile (average recreational climber)."""
    return ClimberProfile.default_profile()
