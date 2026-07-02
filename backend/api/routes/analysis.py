from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated, Optional

import anthropic
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from analytics.analyzer import AnalyticsService
from config import Settings, get_settings
from models.analysis import AnalysisRequest, AnalysisResult
from models.beta import BetaType
from models.climber import ClimberProfile
from models.routes import BoardType
from solver.beta_solver import BetaSolver
from storage.store import FileStore
from vision.pipeline import VisionPipeline

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


def get_store(settings: Annotated[Settings, Depends(get_settings)]) -> FileStore:
    return FileStore(settings.storage_dir)


def get_anthropic_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> anthropic.Anthropic:
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ANTHROPIC_API_KEY not configured. Set it in .env file.",
        )
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


@router.post("/upload", response_model=AnalysisResult, status_code=status.HTTP_201_CREATED)
async def upload_and_analyze(
    files: list[UploadFile] = File(..., description="Climbing wall images (JPEG/PNG/WebP)"),
    climber_profile_id: Optional[str] = Form(default=None),
    board_type: str = Form(default="unknown"),
    notes: Optional[str] = Form(default=None),
    beta_types: str = Form(default="high_percentage,energy_efficient"),
    settings: Settings = Depends(get_settings),
    store: FileStore = Depends(get_store),
    client: anthropic.Anthropic = Depends(get_anthropic_client),
) -> AnalysisResult:
    """Upload images and run complete analysis pipeline.

    Accepts 1-10 images. Runs CV pipeline, identifies route,
    generates personalized beta.
    """
    if not files:
        raise HTTPException(status_code=400, detail="At least one image file is required")

    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 images per analysis")

    analysis_id = f"analysis_{uuid.uuid4().hex[:8]}"

    # --- Save uploaded files ---
    saved_paths: list[Path] = []
    for file in files:
        if file.content_type and not file.content_type.startswith(("image/", "video/")):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.content_type}. Only images are supported.",
            )

        max_bytes = settings.max_image_size_mb * 1024 * 1024
        content = await file.read()
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} exceeds maximum size of {settings.max_image_size_mb}MB",
            )

        path = store.save_image(content, file.filename or "image.jpg", analysis_id)
        saved_paths.append(path)

    # --- Parse board type ---
    try:
        board = BoardType(board_type)
    except ValueError:
        board = BoardType.UNKNOWN

    # --- Parse beta types ---
    beta_type_list: list[BetaType] = []
    for bt_str in beta_types.split(","):
        bt_str = bt_str.strip()
        try:
            beta_type_list.append(BetaType(bt_str))
        except ValueError:
            pass
    if not beta_type_list:
        beta_type_list = [BetaType.HIGH_PERCENTAGE, BetaType.ENERGY_EFFICIENT]

    # --- Run vision pipeline ---
    vision_pipeline = VisionPipeline(client)
    vision_result = await vision_pipeline.process_images(saved_paths, board)

    # --- Load climber profile ---
    profile: ClimberProfile = ClimberProfile.default_profile()
    if climber_profile_id:
        loaded = store.load_profile(climber_profile_id)
        if loaded:
            profile = loaded

    # --- Generate beta ---
    betas = []
    if vision_result.active_route:
        solver = BetaSolver(client)
        betas = await solver.solve(vision_result.active_route, profile, beta_type_list)

    # --- Compute difficulty ---
    analytics = AnalyticsService()
    difficulty = None
    if vision_result.active_route:
        difficulty = analytics.compute_difficulty_analysis(vision_result.active_route, betas)

    # --- Build result ---
    request = AnalysisRequest(
        image_paths=[str(p) for p in saved_paths],
        climber_profile_id=climber_profile_id,
        board_type=board,
        notes=notes,
        beta_types_requested=[bt.value for bt in beta_type_list],
    )

    result = AnalysisResult(
        id=analysis_id,
        request=request,
        vision_result=vision_result,
        betas=betas,
        difficulty=difficulty,
        climber_profile_id=profile.id,
    )

    store.save_analysis(result)
    return result


@router.post("/analyze", response_model=AnalysisResult, status_code=status.HTTP_201_CREATED)
async def analyze_existing(
    request: AnalysisRequest,
    settings: Settings = Depends(get_settings),
    store: FileStore = Depends(get_store),
    client: anthropic.Anthropic = Depends(get_anthropic_client),
) -> AnalysisResult:
    """Analyze previously uploaded images by path.

    Use this to re-run analysis with a different climber profile or beta types.
    """
    image_paths = [Path(p) for p in request.image_paths]

    missing = [p for p in image_paths if not p.exists()]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Image files not found: {[str(p) for p in missing]}",
        )

    vision_pipeline = VisionPipeline(client)
    vision_result = await vision_pipeline.process_images(image_paths, request.board_type)

    profile: ClimberProfile = ClimberProfile.default_profile()
    if request.climber_profile_id:
        loaded = store.load_profile(request.climber_profile_id)
        if loaded:
            profile = loaded

    betas = []
    if vision_result.active_route:
        solver = BetaSolver(client)
        beta_types = []
        for bt_str in request.beta_types_requested:
            try:
                beta_types.append(BetaType(bt_str))
            except ValueError:
                pass
        if not beta_types:
            beta_types = [BetaType.HIGH_PERCENTAGE]
        betas = await solver.solve(vision_result.active_route, profile, beta_types)

    analytics = AnalyticsService()
    difficulty = None
    if vision_result.active_route:
        difficulty = analytics.compute_difficulty_analysis(vision_result.active_route, betas)

    analysis_id = f"analysis_{uuid.uuid4().hex[:8]}"
    result = AnalysisResult(
        id=analysis_id,
        request=request,
        vision_result=vision_result,
        betas=betas,
        difficulty=difficulty,
        climber_profile_id=profile.id,
    )
    store.save_analysis(result)
    return result


@router.get("/", response_model=list[dict])
async def list_analyses(
    store: Annotated[FileStore, Depends(get_store)],
) -> list[dict]:
    """List all analyses (summary view)."""
    analyses = store.list_analyses()
    return [
        {
            "id": a.id,
            "created_at": a.created_at.isoformat(),
            "grade_estimate": a.difficulty.grade_v_estimate if a.difficulty else None,
            "grade_font": a.difficulty.grade_font_estimate if a.difficulty else None,
            "overall_confidence": a.vision_result.overall_confidence,
            "hold_count": len(a.vision_result.holds),
            "beta_count": len(a.betas),
            "image_path": a.vision_result.image_path,
        }
        for a in analyses
    ]


@router.get("/{analysis_id}", response_model=AnalysisResult)
async def get_analysis(
    analysis_id: str,
    store: Annotated[FileStore, Depends(get_store)],
) -> AnalysisResult:
    result = store.load_analysis(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Analysis '{analysis_id}' not found")
    return result


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analysis(
    analysis_id: str,
    store: Annotated[FileStore, Depends(get_store)],
) -> None:
    if not store.delete_analysis(analysis_id):
        raise HTTPException(status_code=404, detail=f"Analysis '{analysis_id}' not found")
