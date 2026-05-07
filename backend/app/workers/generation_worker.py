import asyncio
import logging
import socket

from app.config import get_settings
from app.db.session import get_session_factory, init_db
from app.repositories.generation_jobs import acquire_next_queued_job, fail_stale_running_jobs
from app.repositories.uploads import cleanup_expired_uploads
from app.services.generation_runner import run_generation_job

logger = logging.getLogger("generation_worker")


async def worker_loop() -> None:
    settings = get_settings()
    init_db(settings)
    worker_id = f"{settings.worker_id}-{socket.gethostname()}"
    logger.info("Generation worker started: %s", worker_id)

    while True:
        session = get_session_factory(settings)()
        try:
            failed_count = fail_stale_running_jobs(session, stale_after_seconds=settings.worker_stale_after_seconds)
            if failed_count:
                logger.warning("Marked %s stale running jobs as failed", failed_count)
            cleaned_uploads = cleanup_expired_uploads(session)
            if cleaned_uploads:
                logger.info("Cleaned %s expired uploads", cleaned_uploads)

            job = acquire_next_queued_job(session, worker_id=worker_id)
            if job is None:
                await asyncio.sleep(settings.worker_poll_interval_seconds)
                continue

            logger.info("Running generation job %s", job.id)
            await run_generation_job(session=session, job=job, settings=settings)
        except Exception:
            logger.exception("Worker loop iteration failed")
            await asyncio.sleep(settings.worker_poll_interval_seconds)
        finally:
            session.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(worker_loop())


if __name__ == "__main__":
    main()
