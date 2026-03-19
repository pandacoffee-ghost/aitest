from typing import List, Optional
from sqlalchemy.orm import Session

from bis.models.models import IntelligenceSourceModel
from bis.models.schemas import IntelligenceSourceCreate, IntelligenceSourceUpdate
from bis.repositories.repositories import SourceRepository


class SourceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SourceRepository(db)

    def create(self, data: IntelligenceSourceCreate) -> IntelligenceSourceModel:
        model = IntelligenceSourceModel(
            name=data.name,
            url=data.url,
            source_type=data.source_type.value,
            采集周期=data.采集周期,
            headers=data.headers,
            cookies=data.cookies,
        )
        return self.repo.create(model)

    def get_by_id(self, id: str) -> Optional[IntelligenceSourceModel]:
        return self.repo.get_by_id(id)

    def get_all(self, skip: int = 0, limit: int = 100) -> List[IntelligenceSourceModel]:
        return self.repo.get_all(skip, limit)

    def get_enabled(self) -> List[IntelligenceSourceModel]:
        return self.repo.get_enabled()

    def update(self, id: str, data: IntelligenceSourceUpdate) -> Optional[IntelligenceSourceModel]:
        model = self.repo.get_by_id(id)
        if not model:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "source_type" and value:
                setattr(model, field, value.value)
            else:
                setattr(model, field, value)

        return self.repo.update(model)

    def delete(self, id: str) -> bool:
        return self.repo.delete(id)

    def enable(self, id: str) -> Optional[IntelligenceSourceModel]:
        model = self.repo.get_by_id(id)
        if not model:
            return None
        model.enabled = True
        return self.repo.update(model)

    def disable(self, id: str) -> Optional[IntelligenceSourceModel]:
        model = self.repo.get_by_id(id)
        if not model:
            return None
        model.enabled = False
        return self.repo.update(model)
