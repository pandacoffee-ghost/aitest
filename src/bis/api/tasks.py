from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from bis.core.database import get_db
from bis.core.task_runner import submit_task
from bis.models.schemas import (
    CollectionTaskCreate,
    CollectionTaskUpdate,
    CollectionTask,
    TaskListResponse,
    CollectionTaskRun,
    TaskRunSummary,
    TaskBatchActionRequest,
    TaskRuleBindingRequest,
)
from bis.services.task_service import TaskService

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.post("", response_model=CollectionTask, status_code=status.HTTP_201_CREATED)
def create_task(data: CollectionTaskCreate, db: Session = Depends(get_db)):
    service = TaskService(db)
    try:
        return service.create(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=TaskListResponse)
def list_tasks(
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
    rule_id: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    service = TaskService(db)
    return service.get_all(skip=skip, limit=limit, status=status, rule_id=rule_id, q=q)


@router.get("/{task_id}", response_model=CollectionTask)
def get_task(task_id: str, db: Session = Depends(get_db)):
    service = TaskService(db)
    task = service.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/bind-rule", response_model=List[CollectionTask])
def bind_rule(data: TaskRuleBindingRequest, db: Session = Depends(get_db)):
    service = TaskService(db)
    return service.bind_rule(data.task_ids, data.rule_id)


@router.post("/batch-pause", response_model=List[CollectionTask])
def batch_pause(data: TaskBatchActionRequest, db: Session = Depends(get_db)):
    service = TaskService(db)
    try:
        return service.batch_pause(data.task_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch-resume", response_model=List[CollectionTask])
def batch_resume(data: TaskBatchActionRequest, db: Session = Depends(get_db)):
    service = TaskService(db)
    try:
        return service.batch_resume(data.task_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch-run", response_model=List[CollectionTask])
def batch_run(data: TaskBatchActionRequest, db: Session = Depends(get_db)):
    service = TaskService(db)
    try:
        tasks = service.batch_run(data.task_ids)
        for task in tasks:
            submit_task(task.id)
        return tasks
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch-cancel", response_model=List[CollectionTask])
def batch_cancel(data: TaskBatchActionRequest, db: Session = Depends(get_db)):
    service = TaskService(db)
    try:
        return service.batch_cancel(data.task_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{task_id}", response_model=CollectionTask)
def update_task(task_id: str, data: CollectionTaskUpdate, db: Session = Depends(get_db)):
    service = TaskService(db)
    try:
        task = service.update(task_id, data)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, db: Session = Depends(get_db)):
    service = TaskService(db)
    if not service.delete(task_id):
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/{task_id}/pause", response_model=CollectionTask)
def pause_task(task_id: str, db: Session = Depends(get_db)):
    service = TaskService(db)
    try:
        task = service.pause(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{task_id}/resume", response_model=CollectionTask)
def resume_task(task_id: str, db: Session = Depends(get_db)):
    service = TaskService(db)
    try:
        task = service.resume(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{task_id}/cancel", response_model=CollectionTask)
def cancel_task(task_id: str, db: Session = Depends(get_db)):
    service = TaskService(db)
    try:
        task = service.cancel(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{task_id}/run", response_model=CollectionTask)
def run_task(task_id: str, db: Session = Depends(get_db)):
    service = TaskService(db)
    try:
        task = service.queue_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        submit_task(task_id)
        return task
    except ValueError as e:
        detail = str(e)
        if "not found" in detail:
            raise HTTPException(status_code=404, detail="Task not found")
        raise HTTPException(status_code=400, detail=detail)


@router.get("/{task_id}/runs", response_model=List[CollectionTaskRun])
def list_task_runs(task_id: str, db: Session = Depends(get_db)):
    service = TaskService(db)
    task = service.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return service.get_runs(task_id)


@router.get("/{task_id}/run-summary", response_model=TaskRunSummary)
def get_task_run_summary(task_id: str, db: Session = Depends(get_db)):
    service = TaskService(db)
    summary = service.get_run_summary(task_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Task not found")
    return summary
