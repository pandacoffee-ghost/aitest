from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from bis.core.database import get_db
from bis.models.schemas import IntelligenceSourceCreate, IntelligenceSourceUpdate, IntelligenceSource
from bis.services.source_service import SourceService

router = APIRouter(prefix="/api/v1/sources", tags=["sources"])


@router.post("", response_model=IntelligenceSource, status_code=status.HTTP_201_CREATED)
def create_source(data: IntelligenceSourceCreate, db: Session = Depends(get_db)):
    service = SourceService(db)
    return service.create(data)


@router.get("", response_model=List[IntelligenceSource])
def list_sources(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    service = SourceService(db)
    return service.get_all(skip, limit)


@router.get("/{source_id}", response_model=IntelligenceSource)
def get_source(source_id: str, db: Session = Depends(get_db)):
    service = SourceService(db)
    source = service.get_by_id(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.put("/{source_id}", response_model=IntelligenceSource)
def update_source(source_id: str, data: IntelligenceSourceUpdate, db: Session = Depends(get_db)):
    service = SourceService(db)
    source = service.update(source_id, data)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(source_id: str, db: Session = Depends(get_db)):
    service = SourceService(db)
    if not service.delete(source_id):
        raise HTTPException(status_code=404, detail="Source not found")


@router.post("/{source_id}/enable", response_model=IntelligenceSource)
def enable_source(source_id: str, db: Session = Depends(get_db)):
    service = SourceService(db)
    source = service.enable(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.post("/{source_id}/disable", response_model=IntelligenceSource)
def disable_source(source_id: str, db: Session = Depends(get_db)):
    service = SourceService(db)
    source = service.disable(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source
