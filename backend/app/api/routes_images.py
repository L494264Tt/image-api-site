import asyncio
import json
from datetime import datetime, timezone

import zipfile
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.config import Settings, get_settings
from app.db.session import get_session_factory
from app.errors import UpstreamAPIError
from app.model_capabilities import image_to_image_fallback_model
from app.models.user import User
from app.repositories.generation_jobs import count_active_generation_jobs_for_user, create_generation_job, get_generation_job_for_user
from app.repositories.generation_jobs import cancel_generation_job, list_generation_jobs_for_user, retry_generation_job
from app.repositories.image_generations import (
    create_image_generation,
    get_image_for_user,
    list_images_for_user,
    set_image_favorite,
    soft_delete_images_for_user,
)
from app.services.error_mapper import friendly_upstream_error
from app.schemas import (
    BulkDeleteRequest,
    BulkDeleteResponse,
    GenerationJobEventsTokenResponse,
    FavoriteRequest,
    GenerationJobResponse,
    ImageGenerationRequest,
    ImageGenerationResponse,
    ImageHistoryItem,
    ImageHistoryResponse,
)
from app.services.image_storage import delete_image_file, ensure_thumbnail, resolve_storage_path, save_base64_image, thumbnail_path_for
from app.services.generation_runner import hydrate_request_uploads
from app.services.openai_images import OpenAIImageService
from app.services.auth import InvalidTokenError, create_job_events_token, decode_job_events_token

router = APIRouter(prefix="/api/images", tags=["images"])

TERMINAL_JOB_STATUSES = {"succeeded", "failed", "canceled"}


def get_image_service(settings: Settings = Depends(get_settings)) -> OpenAIImageService:
    return OpenAIImageService(settings)


def history_item_from_record(item) -> ImageHistoryItem:
    return ImageHistoryItem(
        id=item.id,
        prompt=item.prompt,
        revised_prompt=item.revised_prompt,
        model=item.model,
        requested_model=item.requested_model,
        endpoint_type=item.endpoint_type,
        size=item.size,
        mime_type=item.mime_type,
        image_url=f"/api/images/{item.id}/file",
        thumbnail_url=f"/api/images/{item.id}/thumbnail",
        is_favorite=item.is_favorite,
        created_at=item.created_at,
    )


def job_response_from_record(session: Session, job) -> GenerationJobResponse:
    image = None
    if job.image_generation_id is not None:
        item = get_image_for_user(session, image_id=job.image_generation_id, user_id=job.user_id)
        if item is not None:
            image = history_item_from_record(item)
    return GenerationJobResponse(
        id=job.id,
        status=job.status,
        progress_message=job.progress_message,
        error_message=job.error_message,
        error_code=job.error_code,
        error_category=job.error_category,
        raw_error_message=None,
        attempt_count=job.attempt_count,
        max_attempts=job.max_attempts,
        requested_model=job.model,
        effective_model=job.effective_model,
        endpoint_type=job.endpoint_type,
        image=image,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


def format_sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def reject_inline_reference_images(request: ImageGenerationRequest) -> None:
    if any(reference_image.data_url for reference_image in request.reference_images):
        raise HTTPException(status_code=400, detail="参考图必须先上传，并通过 upload_id 引用。")


def enforce_generation_quota(session: Session, *, user_id: int, settings: Settings) -> None:
    active_jobs = count_active_generation_jobs_for_user(session, user_id=user_id)
    if active_jobs >= settings.max_active_generation_jobs_per_user:
        raise HTTPException(status_code=429, detail="当前生成队列已满，请等待已有任务完成后再提交。")


@router.post("/generation-jobs", response_model=GenerationJobResponse, status_code=202)
async def enqueue_image_generation(
    request: ImageGenerationRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> GenerationJobResponse:
    reject_inline_reference_images(request)
    enforce_generation_quota(session, user_id=user.id, settings=settings)
    job = create_generation_job(
        session,
        user_id=user.id,
        prompt=request.prompt,
        negative_prompt=request.negative_prompt,
        model=request.model or settings.upstream_model,
        size=request.size,
        quality=request.quality,
        request_payload=request.model_dump(mode="json", exclude_none=True),
        max_attempts=settings.worker_max_attempts,
    )
    return job_response_from_record(session, job)


@router.get("/generation-jobs/{job_id}", response_model=GenerationJobResponse)
def generation_job_detail(
    job_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> GenerationJobResponse:
    job = get_generation_job_for_user(session, job_id=job_id, user_id=user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    return job_response_from_record(session, job)


@router.post("/generation-jobs/{job_id}/events-token", response_model=GenerationJobEventsTokenResponse)
def create_generation_job_events_token(
    job_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> GenerationJobEventsTokenResponse:
    job = get_generation_job_for_user(session, job_id=job_id, user_id=user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    return GenerationJobEventsTokenResponse(
        token=create_job_events_token(user, job_id=job_id, settings=settings),
        expires_in_seconds=300,
    )


@router.get("/generation-jobs/{job_id}/events")
async def generation_job_events(
    job_id: int,
    token: str = Query(min_length=1),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    try:
        payload = decode_job_events_token(token, job_id=job_id, settings=settings)
        user_id = int(payload["sub"])
    except (InvalidTokenError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=401, detail="Invalid event token") from exc

    session_factory = get_session_factory(settings)
    with session_factory() as session:
        if get_generation_job_for_user(session, job_id=job_id, user_id=user_id) is None:
            raise HTTPException(status_code=404, detail="Generation job not found")

    async def event_stream():
        last_payload: dict | None = None
        while True:
            with session_factory() as session:
                job = get_generation_job_for_user(session, job_id=job_id, user_id=user_id)
                if job is None:
                    yield format_sse_event("error", {"message": "Generation job not found"})
                    return
                payload = job_response_from_record(session, job).model_dump(mode="json")

            if payload != last_payload:
                event = "done" if payload["status"] in TERMINAL_JOB_STATUSES else "job"
                yield format_sse_event(event, payload)
                last_payload = payload
            if payload["status"] in TERMINAL_JOB_STATUSES:
                return
            await asyncio.sleep(2)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/generation-jobs", response_model=list[GenerationJobResponse])
def generation_jobs(
    limit: int = Query(default=20, ge=1, le=50),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[GenerationJobResponse]:
    return [job_response_from_record(session, job) for job in list_generation_jobs_for_user(session, user_id=user.id, limit=limit)]


@router.post("/generation-jobs/{job_id}/cancel", response_model=GenerationJobResponse)
def cancel_job(
    job_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> GenerationJobResponse:
    job = cancel_generation_job(session, job_id=job_id, user_id=user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    return job_response_from_record(session, job)


@router.post("/generation-jobs/{job_id}/retry", response_model=GenerationJobResponse, status_code=202)
def retry_job(
    job_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> GenerationJobResponse:
    job = retry_generation_job(session, job_id=job_id, user_id=user.id, max_attempts=settings.worker_max_attempts)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found or cannot be retried")
    return job_response_from_record(session, job)


@router.post("/generations", response_model=ImageGenerationResponse)
async def create_image(
    request: ImageGenerationRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    service: OpenAIImageService = Depends(get_image_service),
) -> ImageGenerationResponse:
    reject_inline_reference_images(request)
    try:
        request = hydrate_request_uploads(session, user_id=user.id, request=request)
        requested_model = request.model or settings.upstream_model
        if request.reference_images:
            request.model = image_to_image_fallback_model(settings.image_model_list(), requested_model)
        data = await service.generate_image(request)
    except UpstreamAPIError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "message": friendly_upstream_error(exc.message),
                "type": "upstream_error",
                "status_code": exc.status_code,
            },
        ) from exc

    image = data["data"][0]
    encoded = image.get("b64_json")
    if not encoded:
        raise HTTPException(status_code=502, detail="Upstream response did not include an image")

    created_at = datetime.fromtimestamp(data["created"], tz=timezone.utc)
    saved = save_base64_image(
        base_dir=settings.image_storage_dir,
        user_id=user.id,
        created_at=created_at,
        encoded_image=encoded,
        mime_type=image.get("mime_type") or "image/png",
    )
    try:
        record = create_image_generation(
            session,
            user_id=user.id,
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            revised_prompt=image.get("revised_prompt"),
            model=request.model or settings.upstream_model,
            requested_model=requested_model,
            endpoint_type=service.endpoint_type_for_request(request),
            responses_model=settings.upstream_responses_model,
            size=request.size,
            quality=request.quality,
            mime_type=saved.mime_type,
            storage_path=str(saved.absolute_path),
            file_name=saved.file_name,
            file_size_bytes=saved.file_size_bytes,
        )
        ensure_thumbnail(str(saved.absolute_path))
    except Exception:
        delete_image_file(str(saved.absolute_path))
        raise

    return ImageGenerationResponse(
        created=data["created"],
        data=[
            {
                "url": f"/api/images/{record.id}/file",
                "b64_json": None,
                "mime_type": saved.mime_type,
                "revised_prompt": image.get("revised_prompt"),
            }
        ],
    )


@router.get("/history", response_model=ImageHistoryResponse)
def history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    model: str | None = Query(default=None),
    size: str | None = Query(default=None),
    favorite: bool | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ImageHistoryResponse:
    items, total = list_images_for_user(
        session,
        user_id=user.id,
        page=page,
        page_size=page_size,
        search=search,
        model=model,
        size=size,
        favorite=favorite,
        created_from=created_from,
        created_to=created_to,
    )
    return ImageHistoryResponse(
        items=[history_item_from_record(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
def bulk_delete_images(
    request: BulkDeleteRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> BulkDeleteResponse:
    return BulkDeleteResponse(deleted=soft_delete_images_for_user(session, image_ids=request.image_ids, user_id=user.id))


@router.post("/bulk-download")
def bulk_download_images(
    request: BulkDeleteRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    if len(request.image_ids) > settings.max_bulk_download_images:
        raise HTTPException(status_code=413, detail="一次最多下载 50 张图片。")

    buffer = BytesIO()
    total_bytes = 0
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for image_id in request.image_ids:
            item = get_image_for_user(session, image_id=image_id, user_id=user.id)
            if item is None:
                continue
            path = resolve_storage_path(settings.image_storage_dir, item.storage_path)
            if path.exists():
                total_bytes += path.stat().st_size
                if total_bytes > settings.max_bulk_download_bytes:
                    raise HTTPException(status_code=413, detail="批量下载文件过大，请减少选择数量。")
                archive.write(path, arcname=item.file_name)
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="image-history.zip"'},
    )


@router.get("/{image_id}", response_model=ImageHistoryItem)
def image_detail(
    image_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ImageHistoryItem:
    item = get_image_for_user(session, image_id=image_id, user_id=user.id)
    if item is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return history_item_from_record(item)


@router.patch("/{image_id}/favorite", response_model=ImageHistoryItem)
def favorite_image(
    image_id: int,
    request: FavoriteRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ImageHistoryItem:
    item = set_image_favorite(session, image_id=image_id, user_id=user.id, is_favorite=request.is_favorite)
    if item is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return history_item_from_record(item)


@router.get("/{image_id}/file")
def image_file(
    image_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    item = get_image_for_user(session, image_id=image_id, user_id=user.id)
    if item is None:
        raise HTTPException(status_code=404, detail="Image not found")

    file_path = resolve_storage_path(settings.image_storage_dir, item.storage_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image file missing")

    return FileResponse(path=file_path, media_type=item.mime_type, filename=item.file_name)


@router.get("/{image_id}/thumbnail")
def image_thumbnail(
    image_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    item = get_image_for_user(session, image_id=image_id, user_id=user.id)
    if item is None:
        raise HTTPException(status_code=404, detail="Image not found")

    file_path = resolve_storage_path(settings.image_storage_dir, item.storage_path)
    thumbnail_path = ensure_thumbnail(str(file_path)) or thumbnail_path_for(str(file_path))
    if not thumbnail_path.exists():
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Image file missing")
        return FileResponse(path=file_path, media_type=item.mime_type, filename=item.file_name)

    return FileResponse(path=thumbnail_path, media_type="image/jpeg", filename=thumbnail_path.name)
