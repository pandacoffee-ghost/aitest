from concurrent.futures import ThreadPoolExecutor

from bis.core.config import get_settings
from bis.core.database import SessionLocal

settings = get_settings()
executor = ThreadPoolExecutor(max_workers=settings.task.max_concurrent)


def _run_task(task_id: str) -> None:
    from bis.services.scraper_service import ScraperService
    from bis.services.task_service import TaskService

    db = SessionLocal()
    try:
        service = TaskService(db)
        scraper = ScraperService(db)
        service.execute_task(task_id, scraper)
    finally:
        db.close()


def submit_task(task_id: str) -> None:
    executor.submit(_run_task, task_id)


def shutdown_task_runner() -> None:
    executor.shutdown(wait=False, cancel_futures=False)
