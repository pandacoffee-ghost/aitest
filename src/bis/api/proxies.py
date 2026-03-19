from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from bis.core.database import get_db
from bis.models.schemas import ProxyCreate, Proxy
from bis.services.proxy_service import ProxyService

router = APIRouter(prefix="/api/v1/proxies", tags=["proxies"])


@router.post("", response_model=Proxy, status_code=status.HTTP_201_CREATED)
def create_proxy(data: ProxyCreate, db: Session = Depends(get_db)):
    service = ProxyService(db)
    try:
        return service.create(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[Proxy])
def list_proxies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    service = ProxyService(db)
    return service.get_all(skip, limit)


@router.get("/available", response_model=List[Proxy])
def list_available_proxies(db: Session = Depends(get_db)):
    service = ProxyService(db)
    return service.get_available()


@router.get("/{proxy_id}", response_model=Proxy)
def get_proxy(proxy_id: str, db: Session = Depends(get_db)):
    service = ProxyService(db)
    proxy = service.get_by_id(proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return proxy


@router.delete("/{proxy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_proxy(proxy_id: str, db: Session = Depends(get_db)):
    service = ProxyService(db)
    if not service.delete(proxy_id):
        raise HTTPException(status_code=404, detail="Proxy not found")


@router.post("/batch", response_model=List[Proxy], status_code=status.HTTP_201_CREATED)
def create_proxies_batch(data: List[ProxyCreate], db: Session = Depends(get_db)):
    service = ProxyService(db)
    results = []
    for item in data:
        try:
            results.append(service.create(item))
        except Exception:
            continue
    return results
