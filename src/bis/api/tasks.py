from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from bis.core.database import get_db
from bis.models.schemas import CollectionTaskCreate, CollectionTaskUpdate, CollectionTask
from bis.services.task_service import TaskService

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.post("", response_model=CollectionTask, status_code=status.HTTP_201_CREATED)
def create_task(data: CollectionTaskCreate, db: Session = Depends(get_db)):
    service = TaskService(db)
    return service.create(data)


@router.get("", response_model=List[CollectionTask])
def list_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    service = TaskService(db)
    return service.get_all(skip, limit)


@router.get("/{task_id}", response_model=CollectionTask)
def get_task(task_id: str, db: Session = Depends(get_db)):
    service = TaskService(db)
    task = service.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=CollectionTask)
def update_task(task_id: str, data: CollectionTaskUpdate, db: Session = Depends(get_db)):
    service = TaskService(db)
    task = service.update(task_id, data)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


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
        task = service.run_now(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        import asyncio
        from bis.services.scraper_service import ScraperService
        
        def execute_in_background():
            db_session = next(get_db())
            scraper = ScraperService(db_session)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                items = loop.run_until_complete(scraper.execute_task(task))
                service = TaskService(db_session)
                service.mark_completed(task_id)
            except Exception as e:
                print(f"Task execution error: {e}")
                service = TaskService(db_session)
                service.mark_completed(task_id)
            finally:
                loop.close()
                db_session.close()
        
        import threading
        thread = threading.Thread(target=execute_in_background)
        thread.daemon = True
        thread.start()
        
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
