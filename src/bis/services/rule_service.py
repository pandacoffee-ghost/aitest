import asyncio
from typing import List, Optional

from bis.models.models import CollectionRuleModel, CollectionTaskModel
from bis.models.schemas import CollectionRuleCreate, CollectionRuleUpdate, RuleListResponse, RulePreviewRequest
from bis.repositories.repositories import RuleRepository
from bis.services.scraper_service import ScraperService


class RuleService:
    def __init__(self, db):
        self.db = db
        self.repo = RuleRepository(db)
        self.scraper = ScraperService(db)

    def create(self, data: CollectionRuleCreate) -> CollectionRuleModel:
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
        return self.repo.create(model)

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        source_id: Optional[str] = None,
        q: Optional[str] = None,
    ) -> RuleListResponse:
        items = self.repo.get_filtered(skip=skip, limit=limit, source_id=source_id, q=q)
        total = self.repo.count_filtered(source_id=source_id, q=q)
        return RuleListResponse(total=total, items=items)

    def get_by_id(self, rule_id: str) -> Optional[CollectionRuleModel]:
        return self.repo.get_by_id(rule_id)

    def update(self, rule_id: str, data: CollectionRuleUpdate) -> Optional[CollectionRuleModel]:
        model = self.repo.get_by_id(rule_id)
        if not model:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field.endswith("_type") and hasattr(value, "value"):
                setattr(model, field, value.value)
            else:
                setattr(model, field, value)
        return self.repo.update(model)

    def delete(self, rule_id: str) -> bool:
        return self.repo.delete(rule_id)

    def enable(self, rule_id: str) -> Optional[CollectionRuleModel]:
        model = self.repo.get_by_id(rule_id)
        if not model:
            return None
        model.enabled = True
        return self.repo.update(model)

    def disable(self, rule_id: str) -> Optional[CollectionRuleModel]:
        model = self.repo.get_by_id(rule_id)
        if not model:
            return None
        model.enabled = False
        return self.repo.update(model)

    def preview(self, data: RulePreviewRequest):
        html = data.raw_html
        if not html:
            if not data.url:
                raise ValueError("raw_html or url is required for preview")
            html = asyncio.run(self.scraper.fetch_html(data.url))

        rule = CollectionRuleModel(
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

        task = CollectionTaskModel(
            name=f"preview:{data.name}",
            url=data.url,
        )
        task.rule = rule
        return self.scraper.parse_content_with_stats(task, html)
