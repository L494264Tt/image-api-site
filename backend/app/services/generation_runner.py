import base64
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import UpstreamAPIError
from app.models.generation_job import GenerationJob
from app.model_capabilities import image_to_image_fallback_model
from app.repositories.generation_jobs import mark_job_failed, mark_job_succeeded, requeue_or_fail_job, set_job_execution_metadata
from app.repositories.image_generations import create_image_generation
from app.repositories.uploads import list_uploads_for_user, mark_uploads_used
from app.schemas import ImageGenerationRequest
from app.services.error_mapper import map_upstream_error
from app.services.image_storage import delete_image_file, ensure_thumbnail, save_base64_image
from app.services.openai_images import OpenAIImageService


def hydrate_request_uploads(session: Session, *, user_id: int, request: ImageGenerationRequest) -> ImageGenerationRequest:
    upload_ids = [item.upload_id for item in request.reference_images if item.upload_id is not None]
    if not upload_ids:
        return request

    uploads = {upload.id: upload for upload in list_uploads_for_user(session, upload_ids=upload_ids, user_id=user_id)}
    hydrated = request.model_copy(deep=True)
    for reference_image in hydrated.reference_images:
        if reference_image.upload_id is None:
            continue
        upload = uploads.get(reference_image.upload_id)
        if upload is None:
            raise UpstreamAPIError("Reference image upload was not found", status_code=400)
        raw = Path(upload.storage_path).read_bytes()
        reference_image.data_url = f"data:{upload.mime_type};base64,{base64.b64encode(raw).decode()}"
        reference_image.mime_type = upload.mime_type
        reference_image.name = upload.original_name or upload.file_name

    mark_uploads_used(session, upload_ids=upload_ids, user_id=user_id)
    return hydrated


async def run_generation_job(*, session: Session, job: GenerationJob, settings: Settings) -> None:
    try:
        request = ImageGenerationRequest.model_validate(job.request_payload)
        request = hydrate_request_uploads(session, user_id=job.user_id, request=request)
        requested_model = request.model or settings.upstream_model
        if request.reference_images:
            request.model = image_to_image_fallback_model(settings.image_model_list(), requested_model)
        service = OpenAIImageService(settings)
        endpoint_type = service.endpoint_type_for_request(request)
        set_job_execution_metadata(
            session,
            job,
            effective_model=request.model or settings.upstream_model,
            endpoint_type=endpoint_type,
        )
        data = await service.generate_image(request)
        image = data["data"][0]
        encoded = image.get("b64_json")
        if not encoded:
            raise UpstreamAPIError("Upstream response did not include an image", status_code=502)

        created_at = datetime.fromtimestamp(data["created"], tz=timezone.utc)
        saved = save_base64_image(
            base_dir=settings.image_storage_dir,
            user_id=job.user_id,
            created_at=created_at,
            encoded_image=encoded,
            mime_type=image.get("mime_type") or "image/png",
        )
        ensure_thumbnail(str(saved.absolute_path))
        try:
            session.refresh(job)
            if job.status == "canceled":
                delete_image_file(str(saved.absolute_path))
                return
            record = create_image_generation(
                session,
                user_id=job.user_id,
                prompt=request.prompt,
                negative_prompt=request.negative_prompt,
                revised_prompt=image.get("revised_prompt"),
                model=request.model or settings.upstream_model,
                requested_model=requested_model,
                endpoint_type=endpoint_type,
                responses_model=settings.upstream_responses_model,
                size=request.size,
                quality=request.quality,
                mime_type=saved.mime_type,
                storage_path=str(saved.absolute_path),
                file_name=saved.file_name,
                file_size_bytes=saved.file_size_bytes,
            )
        except Exception:
            delete_image_file(str(saved.absolute_path))
            raise

        mark_job_succeeded(session, job, image_generation_id=record.id)
    except UpstreamAPIError as exc:
        mapped = map_upstream_error(exc.message, status_code=exc.status_code)
        requeue_or_fail_job(
            session,
            job,
            message=mapped.message,
            retryable=mapped.retryable,
            error_code=mapped.code,
            error_category=mapped.category,
            raw_error_message=exc.message,
        )
    except Exception as exc:
        mark_job_failed(
            session,
            job,
            message="生成任务异常失败，请稍后重试。",
            error_code="internal_error",
            error_category="internal",
            raw_error_message=str(exc),
        )
