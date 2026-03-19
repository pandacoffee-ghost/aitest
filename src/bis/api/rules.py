from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from bis.core.database import get_db
from bis.models.models import CollectionRuleModel
from bis.models.schemas import CollectionRuleCreate, CollectionRuleUpdate, CollectionRule
from bis.repositories.repositories import SourceRepository

router = APIRouter(prefix="/api/v1/rules", tags=["rules"])


def get_rule_model(source_id: str, db: Session) -> CollectionRuleModel:
    model = CollectionRuleModel(
        source_id=source_id,
        name="Default Rule",
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.post("", response_model=CollectionRule, status_code=status.HTTP_201_CREATED)
def create_rule(data: CollectionRuleCreate, db: Session = Depends(get_db)):
    model = CollectionRuleModel(
        source_id=data.source_id,
        name=data.name,
        list_selector=data.list_selector,
        list_selector_type=data.list_selector_type.value,
        title_selector=data.title_selector,
        title_selector_type=data.title_selector_type.value,
        content_selector=data.content_selector,
        content_selector_type=data.content_selector_type.value,
        link_selector=data.link_selector,
        link_selector_type=data.link_selector_type.value,
        date_selector=data.date_selector,
        date_selector_type=data.date_selector_type.value,
        date_format=data.date_format,
        keyword_match=data.keyword_match,
        keyword_match_type=data.keyword_match_type.value,
        regex_pattern=data.regex_pattern,
        follow_next_page=data.follow_next_page,
        next_page_selector=data.next_page_selector,
        max_pages=data.max_pages,
        priority=data.priority,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.get("/source/{source_id}", response_model=List[CollectionRule])
def list_rules_by_source(source_id: str, db: Session = Depends(get_db)):
    return db.query(CollectionRuleModel).filter(CollectionRuleModel.source_id == source_id).all()


@router.get("/{rule_id}", response_model=CollectionRule)
def get_rule(rule_id: str, db: Session = Depends(get_db)):
    model = db.query(CollectionRuleModel).filter(CollectionRuleModel.id == rule_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Rule not found")
    return model


@router.put("/{rule_id}", response_model=CollectionRule)
def update_rule(rule_id: str, data: CollectionRuleUpdate, db: Session = Depends(get_db)):
    model = db.query(CollectionRuleModel).filter(CollectionRuleModel.id == rule_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field.endswith('_type') and hasattr(value, 'value'):
            setattr(model, field, value.value)
        else:
            setattr(model, field, value)
    
    db.commit()
    db.refresh(model)
    return model


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: str, db: Session = Depends(get_db)):
    model = db.query(CollectionRuleModel).filter(CollectionRuleModel.id == rule_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(model)
    db.commit()
