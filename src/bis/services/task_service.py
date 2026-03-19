from typing import List, Optional
from sqlalchemy.orm import Session

from bis.models.models import CollectionTaskModel, TaskStatus
from bis.models.schemas import CollectionTaskCreate, CollectionTaskUpdate
from bis.repositories.repositories import TaskRepository


class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = TaskRepository(db)

    def create(self, data: CollectionTaskCreate) -> CollectionTaskModel:
        model = CollectionTaskModel(
            name=data.name,
            source_ids=data.source_ids,
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

    def get_all(self, skip: int = 0, limit: int = 100) -> List[CollectionTaskModel]:
        return self.repo.get_all(skip, limit)

    def get_by_status(self, status: TaskStatus) -> List[CollectionTaskModel]:
        return self.repo.get_by_status(status.value)

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
        return self.repo.update(model)

    def run_now(self, id: str) -> Optional[CollectionTaskModel]:
        model = self.repo.get_by_id(id)
        if not model:
            return None
        if model.status == TaskStatus.RUNNING.value:
            raise ValueError(f"Task {id} is already running")
        model.status = TaskStatus.RUNNING.value
        return self.repo.update(model)
