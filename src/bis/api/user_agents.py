from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from bis.core.database import get_db
from bis.models.schemas import UserAgentCreate, UserAgent
from bis.services.ua_service import UserAgentService

router = APIRouter(prefix="/api/v1/user-agents", tags=["user-agents"])


@router.post("", response_model=UserAgent, status_code=status.HTTP_201_CREATED)
def create_ua(data: UserAgentCreate, db: Session = Depends(get_db)):
    service = UserAgentService(db)
    return service.create(data)


@router.get("", response_model=List[UserAgent])
def list_uas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    service = UserAgentService(db)
    return service.get_all(skip, limit)


@router.get("/random", response_model=UserAgent)
def get_random_ua(db: Session = Depends(get_db)):
    service = UserAgentService(db)
    ua = service.get_random()
    if not ua:
        raise HTTPException(status_code=404, detail="No enabled User-Agent found")
    return ua


@router.get("/{ua_id}", response_model=UserAgent)
def get_ua(ua_id: str, db: Session = Depends(get_db)):
    service = UserAgentService(db)
    ua = service.get_by_id(ua_id)
    if not ua:
        raise HTTPException(status_code=404, detail="User-Agent not found")
    return ua


@router.delete("/{ua_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ua(ua_id: str, db: Session = Depends(get_db)):
    service = UserAgentService(db)
    if not service.delete(ua_id):
        raise HTTPException(status_code=404, detail="User-Agent not found")
