from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from bis.core.database import get_db
from bis.models.schemas import (
    CollectionRuleCreate,
    CollectionRuleUpdate,
    CollectionRule,
    RulePreviewRequest,
    RulePreviewResponse,
)
from bis.services.rule_service import RuleService

router = APIRouter(prefix="/api/v1/rules", tags=["rules"])


@router.post("", response_model=CollectionRule, status_code=status.HTTP_201_CREATED)
def create_rule(data: CollectionRuleCreate, db: Session = Depends(get_db)):
    service = RuleService(db)
    return service.create(data)


@router.get("", response_model=List[CollectionRule])
def list_rules(
    skip: int = 0,
    limit: int = 100,
    source_id: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    service = RuleService(db)
    return service.get_all(skip=skip, limit=limit, source_id=source_id, q=q)


@router.get("/source/{source_id}", response_model=List[CollectionRule])
def list_rules_by_source(source_id: str, db: Session = Depends(get_db)):
    service = RuleService(db)
    return service.get_all(source_id=source_id)


@router.get("/{rule_id}", response_model=CollectionRule)
def get_rule(rule_id: str, db: Session = Depends(get_db)):
    service = RuleService(db)
    model = service.get_by_id(rule_id)
    if not model:
        raise HTTPException(status_code=404, detail="Rule not found")
    return model


@router.put("/{rule_id}", response_model=CollectionRule)
def update_rule(rule_id: str, data: CollectionRuleUpdate, db: Session = Depends(get_db)):
    service = RuleService(db)
    model = service.update(rule_id, data)
    if not model:
        raise HTTPException(status_code=404, detail="Rule not found")
    return model


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: str, db: Session = Depends(get_db)):
    service = RuleService(db)
    if not service.delete(rule_id):
        raise HTTPException(status_code=404, detail="Rule not found")


@router.post("/{rule_id}/enable", response_model=CollectionRule)
def enable_rule(rule_id: str, db: Session = Depends(get_db)):
    service = RuleService(db)
    rule = service.enable(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.post("/{rule_id}/disable", response_model=CollectionRule)
def disable_rule(rule_id: str, db: Session = Depends(get_db)):
    service = RuleService(db)
    rule = service.disable(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.post("/preview", response_model=RulePreviewResponse)
def preview_rule(data: RulePreviewRequest, db: Session = Depends(get_db)):
    service = RuleService(db)
    try:
        items, stats = service.preview(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return RulePreviewResponse(count=len(items), items=items, **stats)
