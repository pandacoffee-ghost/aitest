import asyncio
import hashlib
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from bis.models.models import CollectionTaskModel, CollectionTaskRunModel, IntelligenceDetailModel, TaskRunStatus, TaskStatus
from bis.models.schemas import CollectionTaskCreate, CollectionTaskUpdate, TaskRunSummary
from bis.repositories.repositories import IntelligenceRepository, TaskRepository, TaskRunRepository


class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = TaskRepository(db)
        self.run_repo = TaskRunRepository(db)
        self.intelligence_repo = IntelligenceRepository(db)

    def create(self, data: CollectionTaskCreate) -> CollectionTaskModel:
        model = CollectionTaskModel(
            name=data.name,
            source_ids=data.source_ids,
            rule_id=data.rule_id,
            url=data.url,
            charset=data.charset,
            list_selector=data.list_selector,
            list_selector_type=data.list_selector_type.value if data.list_selector_type else "css",
            title_selector=data.title_selector,
            title_selector_type=data.title_selector_type.value if data.title_selector_type else "css",
            content_selector=data.content_selector,
            content_selector_type=data.content_selector_type.value if data.content_selector_type else "css",
            link_selector=data.link_selector,
            link_selector_type=data.link_selector_type.value if data.link_selector_type else "css",
            date_selector=data.date_selector,
            date_selector_type=data.date_selector_type.value if data.date_selector_type else "css",
            keywords=data.keywords,
            do_screenshot=data.do_screenshot,
            proxy_enabled=data.proxy_enabled,
            ua_enabled=data.ua_enabled,
            cron_expression=data.cron_expression,
            timeout=data.timeout,
            retry_count=data.retry_count,
            status=TaskStatus.PENDING.value,
        )
        return self.repo.create(model)

    def get_by_id(self, id: str) -> Optional[CollectionTaskModel]:
        return self.repo.get_by_id(id)

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        rule_id: Optional[str] = None,
        q: Optional[str] = None,
    ) -> List[CollectionTaskModel]:
        return self.repo.get_filtered(skip=skip, limit=limit, status=status, rule_id=rule_id, q=q)

    def bind_rule(self, task_ids: List[str], rule_id: str) -> List[CollectionTaskModel]:
        results = []
        for task_id in task_ids:
            model = self.repo.get_by_id(task_id)
            if not model:
                continue
            model.rule_id = rule_id
            results.append(self.repo.update(model))
        return results

    def batch_pause(self, task_ids: List[str]) -> List[CollectionTaskModel]:
        results = []
        for task_id in task_ids:
            task = self.pause(task_id)
            if task:
                results.append(task)
        return results

    def batch_resume(self, task_ids: List[str]) -> List[CollectionTaskModel]:
        results = []
        for task_id in task_ids:
            task = self.resume(task_id)
            if task:
                results.append(task)
        return results

    def batch_run(self, task_ids: List[str]) -> List[CollectionTaskModel]:
        results = []
        for task_id in task_ids:
            task = self.queue_task(task_id)
            if task:
                results.append(task)
        return results

    def batch_cancel(self, task_ids: List[str]) -> List[CollectionTaskModel]:
        results = []
        for task_id in task_ids:
            task = self.cancel(task_id)
            if task:
                results.append(task)
        return results

    def get_by_status(self, status: TaskStatus) -> List[CollectionTaskModel]:
        return self.repo.get_by_status(status.value)

    def get_runs(self, id: str) -> List[CollectionTaskRunModel]:
        return self.run_repo.get_by_task_id(id)

    def get_run_summary(self, id: str) -> Optional[TaskRunSummary]:
        task = self.repo.get_by_id(id)
        if not task:
            return None

        latest_run = task.latest_run
        if not latest_run:
            return TaskRunSummary(task_id=id)

        return TaskRunSummary(
            task_id=id,
            latest_status=TaskRunStatus(latest_run.status),
            started_at=latest_run.started_at,
            finished_at=latest_run.finished_at,
            items_fetched=latest_run.items_fetched,
            items_collected=latest_run.items_collected,
            error_message=latest_run.error_message,
        )

    def update(self, id: str, data: CollectionTaskUpdate) -> Optional[CollectionTaskModel]:
        model = self.repo.get_by_id(id)
        if not model:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(model, field, value)

        return self.repo.update(model)

    def delete(self, id: str) -> bool:
        return self.repo.delete(id)

    def pause(self, id: str) -> Optional[CollectionTaskModel]:
        model = self.repo.get_by_id(id)
        if not model:
            return None
        if model.status != TaskStatus.RUNNING.value:
            raise ValueError(f"Task {id} is not running")
        model.status = TaskStatus.PAUSED.value
        return self.repo.update(model)

    def resume(self, id: str) -> Optional[CollectionTaskModel]:
        model = self.repo.get_by_id(id)
        if not model:
            return None
        if model.status != TaskStatus.PAUSED.value:
            raise ValueError(f"Task {id} is not paused")
        model.status = TaskStatus.PENDING.value
        return self.repo.update(model)

    def cancel(self, id: str) -> Optional[CollectionTaskModel]:
        model = self.repo.get_by_id(id)
        if not model:
            return None
        if model.status in [TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value]:
            raise ValueError(f"Task {id} cannot be cancelled")
        model.status = TaskStatus.CANCELLED.value
        return self.repo.update(model)

    def mark_running(self, id: str) -> Optional[CollectionTaskModel]:
        model = self.repo.get_by_id(id)
        if not model:
            return None
        model.status = TaskStatus.RUNNING.value
        return self.repo.update(model)

    def mark_completed(self, id: str) -> Optional[CollectionTaskModel]:
        model = self.repo.get_by_id(id)
        if not model:
            return None
        model.status = TaskStatus.COMPLETED.value
        model.last_run_at = datetime.utcnow()
        return self.repo.update(model)

    def mark_failed(self, id: str) -> Optional[CollectionTaskModel]:
        model = self.repo.get_by_id(id)
        if not model:
            return None
        model.status = TaskStatus.FAILED.value
        model.last_run_at = datetime.utcnow()
        return self.repo.update(model)

    def run_now(self, id: str) -> Optional[CollectionTaskModel]:
        model = self.repo.get_by_id(id)
        if not model:
            return None
        if model.status == TaskStatus.RUNNING.value:
            raise ValueError(f"Task {id} is already running")
        model.status = TaskStatus.RUNNING.value
        model.last_run_at = datetime.utcnow()
        return self.repo.update(model)

    def queue_task(self, id: str) -> Optional[CollectionTaskModel]:
        model = self.repo.get_by_id(id)
        if not model:
            return None
        if model.status in [TaskStatus.RUNNING.value, TaskStatus.QUEUED.value]:
            raise ValueError(f"Task {id} is already active")
        model.status = TaskStatus.QUEUED.value
        return self.repo.update(model)

    def execute_task(self, id: str, scraper) -> CollectionTaskModel:
        task = self.repo.get_by_id(id)
        if not task:
            raise ValueError(f"Task {id} not found")
        if task.status == TaskStatus.RUNNING.value:
            raise ValueError(f"Task {id} is already running")

        run = CollectionTaskRunModel(
            task_id=task.id,
            status=TaskRunStatus.RUNNING.value,
            started_at=datetime.utcnow(),
        )
        self.run_repo.create(run)
        self.run_now(task.id)

        try:
            items = asyncio.run(scraper.execute_task(task))
            run.items_fetched = len(items or [])
            stored_count = self._persist_items(task, items)
            run.status = TaskRunStatus.COMPLETED.value
            run.finished_at = datetime.utcnow()
            run.items_collected = stored_count
            self.run_repo.update(run)
            task = self.mark_completed(task.id)
        except Exception as exc:
            run.status = TaskRunStatus.FAILED.value
            run.finished_at = datetime.utcnow()
            run.error_message = str(exc)
            self.run_repo.update(run)
            task = self.mark_failed(task.id)

        self.db.refresh(task)
        self.db.refresh(run)
        return task

    def _persist_items(
        self,
        task: CollectionTaskModel,
        items: Optional[List[IntelligenceDetailModel]],
    ) -> int:
        if not items:
            return 0

        stored_count = 0
        for item in items:
            if not item.deduplication_key:
                item.deduplication_key = self._generate_dedup_key(task, item)

            if self.intelligence_repo.exists_by_dedup_key(item.deduplication_key):
                continue

            if item.source_id is None and task.source_ids:
                item.source_id = task.source_ids[0]
            if item.collected_at is None:
                item.collected_at = datetime.utcnow()

            if item.id:
                stored_count += 1
                continue

            self.db.add(item)
            stored_count += 1

        self.db.commit()
        return stored_count

    def _generate_dedup_key(self, task: CollectionTaskModel, item: IntelligenceDetailModel) -> str:
        content = f"{task.id}:{item.title}:{item.raw_data.get('link') if item.raw_data else None}:{item.content}"
        return hashlib.md5(content.encode()).hexdigest()
