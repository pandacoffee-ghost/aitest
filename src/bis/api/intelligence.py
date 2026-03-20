from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from bis.core.database import get_db
from bis.models.schemas import IntelligenceDetail, IntelligenceSearchQuery
from bis.services.intelligence_service import IntelligenceService

router = APIRouter(prefix="/api/v1/intelligence", tags=["intelligence"])


def parse_optional_datetime(value: str | None, field_name: str):
    from datetime import datetime

    if value is None:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name} format. Use ISO 8601.",
        ) from exc


@router.get("", response_model=List[IntelligenceDetail])
def search_intelligence(
    source_id: str = None,
    keyword: str = None,
    start_date: str = None,
    end_date: str = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    query = IntelligenceSearchQuery(
        source_id=source_id,
        keyword=keyword,
        start_date=parse_optional_datetime(start_date, "start_date"),
        end_date=parse_optional_datetime(end_date, "end_date"),
        page=page,
        page_size=page_size,
    )
    service = IntelligenceService(db)
    return service.search(query)


@router.get("/{intelligence_id}", response_model=IntelligenceDetail)
def get_intelligence(intelligence_id: str, db: Session = Depends(get_db)):
    service = IntelligenceService(db)
    item = service.get_by_id(intelligence_id)
    if not item:
        raise HTTPException(status_code=404, detail="Intelligence not found")
    return item


@router.delete("/{intelligence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_intelligence(intelligence_id: str, db: Session = Depends(get_db)):
    service = IntelligenceService(db)
    if not service.delete(intelligence_id):
        raise HTTPException(status_code=404, detail="Intelligence not found")
