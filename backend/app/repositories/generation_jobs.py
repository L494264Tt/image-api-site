from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.generation_job import GenerationJob


def create_generation_job(
    session: Session,
    *,
    user_id: int,
    prompt: str,
    negative_prompt: str | None,
    model: str,
    size: str,
    quality: str | None,
    request_payload: dict,
    max_attempts: int = 2,
) -> GenerationJob:
    job = GenerationJob(
        user_id=user_id,
        prompt=prompt,
        negative_prompt=negative_prompt,
        model=model,
        size=size,
        quality=quality,
        request_payload=request_payload,
        max_attempts=max_attempts,
        status="queued",
        progress_message="已加入生成队列",
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def get_generation_job_for_user(
    session: Session,
    *,
    job_id: int,
    user_id: int,
    include_deleted: bool = False,
) -> GenerationJob | None:
    filters = [
        GenerationJob.id == job_id,
        GenerationJob.user_id == user_id,
    ]
    if not include_deleted:
        filters.append(GenerationJob.deleted_at.is_(None))
    return session.scalar(
        select(GenerationJob).where(*filters)
    )


def list_generation_jobs_for_user(
    session: Session,
    *,
    user_id: int,
    limit: int = 20,
    include_deleted: bool = False,
) -> list[GenerationJob]:
    filters = [
        GenerationJob.user_id == user_id,
        GenerationJob.deleted_at.is_not(None) if include_deleted else GenerationJob.deleted_at.is_(None),
    ]
    return list(
        session.scalars(
            select(GenerationJob)
            .where(*filters)
            .order_by(GenerationJob.created_at.desc(), GenerationJob.id.desc())
            .limit(limit)
        )
    )


def count_active_generation_jobs_for_user(session: Session, *, user_id: int) -> int:
    return session.scalar(
        select(func.count())
        .select_from(GenerationJob)
        .where(
            GenerationJob.user_id == user_id,
            GenerationJob.deleted_at.is_(None),
            GenerationJob.status.in_(("queued", "running")),
        )
    ) or 0


def cancel_generation_job(session: Session, *, job_id: int, user_id: int) -> GenerationJob | None:
    job = get_generation_job_for_user(session, job_id=job_id, user_id=user_id)
    if job is None or job.status not in {"queued", "running"}:
        return job
    job.status = "canceled"
    job.progress_message = "已取消"
    job.locked_by = None
    job.locked_at = None
    job.completed_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(job)
    return job


def retry_generation_job(session: Session, *, job_id: int, user_id: int, max_attempts: int = 2) -> GenerationJob | None:
    source = get_generation_job_for_user(session, job_id=job_id, user_id=user_id)
    if source is None or source.status not in {"failed", "canceled"}:
        return None
    return create_generation_job(
        session,
        user_id=user_id,
        prompt=source.prompt,
        negative_prompt=source.negative_prompt,
        model=source.model,
        size=source.size,
        quality=source.quality,
        request_payload=source.request_payload,
        max_attempts=max_attempts,
    )


def soft_delete_generation_job(session: Session, *, job_id: int, user_id: int) -> GenerationJob | None:
    job = get_generation_job_for_user(session, job_id=job_id, user_id=user_id)
    if job is None:
        return None
    now = datetime.now(timezone.utc)
    if job.status in {"queued", "running"}:
        job.status = "canceled"
        job.progress_message = "已删除"
        job.locked_by = None
        job.locked_at = None
        job.completed_at = now
    job.deleted_at = now
    session.commit()
    session.refresh(job)
    return job


def restore_generation_job(session: Session, *, job_id: int, user_id: int) -> GenerationJob | None:
    job = get_generation_job_for_user(session, job_id=job_id, user_id=user_id, include_deleted=True)
    if job is None or job.deleted_at is None:
        return None
    job.deleted_at = None
    session.commit()
    session.refresh(job)
    return job


def acquire_next_queued_job(session: Session, *, worker_id: str) -> GenerationJob | None:
    job = session.scalar(
        select(GenerationJob)
        .where(GenerationJob.status == "queued", GenerationJob.deleted_at.is_(None))
        .order_by(GenerationJob.created_at.asc(), GenerationJob.id.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if job is None:
        return None
    mark_job_running(session, job, worker_id=worker_id)
    return job


def mark_job_running(session: Session, job: GenerationJob, *, worker_id: str | None = None) -> None:
    job.status = "running"
    job.progress_message = "正在调用上游生成服务"
    job.attempt_count += 1
    job.locked_by = worker_id
    job.locked_at = datetime.now(timezone.utc)
    job.started_at = datetime.now(timezone.utc)
    session.commit()


def set_job_execution_metadata(session: Session, job: GenerationJob, *, effective_model: str, endpoint_type: str) -> None:
    job.effective_model = effective_model
    job.endpoint_type = endpoint_type
    session.commit()


def mark_job_succeeded(session: Session, job: GenerationJob, *, image_generation_id: int) -> None:
    job.status = "succeeded"
    job.progress_message = "生成完成"
    job.image_generation_id = image_generation_id
    job.locked_by = None
    job.locked_at = None
    job.completed_at = datetime.now(timezone.utc)
    session.commit()


def mark_job_failed(
    session: Session,
    job: GenerationJob,
    *,
    message: str,
    error_code: str | None = None,
    error_category: str | None = None,
    raw_error_message: str | None = None,
) -> None:
    job.status = "failed"
    job.progress_message = "生成失败"
    job.error_message = message
    job.error_code = error_code
    job.error_category = error_category
    job.raw_error_message = raw_error_message
    job.locked_by = None
    job.locked_at = None
    job.completed_at = datetime.now(timezone.utc)
    session.commit()


def requeue_or_fail_job(
    session: Session,
    job: GenerationJob,
    *,
    message: str,
    retryable: bool,
    error_code: str | None = None,
    error_category: str | None = None,
    raw_error_message: str | None = None,
) -> None:
    job.locked_by = None
    job.locked_at = None
    job.error_message = message
    job.error_code = error_code
    job.error_category = error_category
    job.raw_error_message = raw_error_message
    if retryable and job.attempt_count < job.max_attempts:
        job.status = "queued"
        job.progress_message = "生成失败，已重新排队重试"
    else:
        job.status = "failed"
        job.progress_message = "生成失败"
        if retryable and job.attempt_count >= job.max_attempts:
            job.error_message = f"{message} 已达到自动重试上限。"
        job.completed_at = datetime.now(timezone.utc)
    session.commit()


def fail_stale_running_jobs(session: Session, *, stale_after_seconds: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=stale_after_seconds)
    jobs = list(
        session.scalars(
            select(GenerationJob).where(
                GenerationJob.status == "running",
                GenerationJob.deleted_at.is_(None),
                GenerationJob.locked_at.is_not(None),
                GenerationJob.locked_at < cutoff,
            )
        )
    )
    for job in jobs:
        job.status = "failed"
        job.progress_message = "生成失败"
        job.error_message = "生成任务超时或 worker 已中断，请重新提交。"
        job.error_code = "worker_stale"
        job.error_category = "timeout"
        job.raw_error_message = "running job exceeded stale timeout"
        job.locked_by = None
        job.locked_at = None
        job.completed_at = datetime.now(timezone.utc)
    session.commit()
    return len(jobs)
