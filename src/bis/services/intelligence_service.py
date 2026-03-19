import hashlib
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from bis.models.models import IntelligenceDetailModel
from bis.models.schemas import IntelligenceDetailBase, IntelligenceSearchQuery
from bis.repositories.repositories import IntelligenceRepository, SourceRepository
from bis.core.config import get_settings

settings = get_settings()


class IntelligenceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = IntelligenceRepository(db)
        self.source_repo = SourceRepository(db)

    def create(self, data: IntelligenceDetailBase, source_id: Optional[str] = None) -> IntelligenceDetailModel:
        dedup_key = self._generate_dedup_key(data, source_id)

        if settings.intelligence.deduplication_enabled:
            if self.repo.exists_by_dedup_key(dedup_key):
                return None

        model = IntelligenceDetailModel(
            source_id=source_id,
            title=data.title,
            content=data.content,
            summary=data.summary[:settings.intelligence.summary_max_length] if data.summary else None,
            keywords=data.keywords,
            entities=data.entities,
            raw_data={},
            collected_at=datetime.utcnow(),
            deduplication_key=dedup_key,
        )
        return self.repo.create(model)

    def _generate_dedup_key(self, data: IntelligenceDetailBase, source_id: Optional[str]) -> str:
        content = f"{source_id}:{data.title}:{data.content}"
        return hashlib.md5(content.encode()).hexdigest()

    def get_by_id(self, id: str) -> Optional[IntelligenceDetailModel]:
        return self.repo.get_by_id(id)

    def search(self, query: IntelligenceSearchQuery) -> List[IntelligenceDetailModel]:
        return self.repo.search(
            source_id=query.source_id,
            keyword=query.keyword,
            start_date=query.start_date,
            end_date=query.end_date,
            skip=(query.page - 1) * query.page_size,
            limit=query.page_size,
        )

    def delete(self, id: str) -> bool:
        return self.repo.delete(id)

    def create_batch(self, items: List[IntelligenceDetailBase], source_id: Optional[str] = None) -> List[IntelligenceDetailModel]:
        results = []
        for item in items:
            created = self.create(item, source_id)
            if created:
                results.append(created)
        return results
