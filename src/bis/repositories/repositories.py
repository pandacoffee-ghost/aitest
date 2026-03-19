from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from bis.models.models import IntelligenceSourceModel, ProxyModel, UserAgentModel, CollectionTaskModel, IntelligenceDetailModel
from bis.repositories.base import BaseRepository


class SourceRepository(BaseRepository[IntelligenceSourceModel]):
    def __init__(self, db: Session):
        super().__init__(IntelligenceSourceModel, db)

    def get_enabled(self) -> List[IntelligenceSourceModel]:
        return self.db.query(self.model).filter(self.model.enabled).all()

    def get_by_ids(self, ids: List[str]) -> List[IntelligenceSourceModel]:
        return self.db.query(self.model).filter(self.model.id.in_(ids)).all()


class ProxyRepository(BaseRepository[ProxyModel]):
    def __init__(self, db: Session):
        super().__init__(ProxyModel, db)

    def get_available(self) -> List[ProxyModel]:
        return (
            self.db.query(self.model)
            .filter(self.model.enabled)
            .filter(self.model.quality_score > 0)
            .all()
        )

    def get_by_ip_port(self, ip: str, port: int) -> Optional[ProxyModel]:
        return (
            self.db.query(self.model)
            .filter(self.model.ip == ip, self.model.port == port)
            .first()
        )


class UserAgentRepository(BaseRepository[UserAgentModel]):
    def __init__(self, db: Session):
        super().__init__(UserAgentModel, db)

    def get_enabled(self) -> List[UserAgentModel]:
        return self.db.query(self.model).filter(self.model.enabled).all()


class TaskRepository(BaseRepository[CollectionTaskModel]):
    def __init__(self, db: Session):
        super().__init__(CollectionTaskModel, db)

    def get_by_status(self, status: str) -> List[CollectionTaskModel]:
        return self.db.query(self.model).filter(self.model.status == status).all()

    def get_running(self) -> List[CollectionTaskModel]:
        return self.get_by_status("running")


class IntelligenceRepository(BaseRepository[IntelligenceDetailModel]):
    def __init__(self, db: Session):
        super().__init__(IntelligenceDetailModel, db)

    def search(
        self,
        source_id: Optional[str] = None,
        keyword: Optional[str] = None,
        start_date=None,
        end_date=None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[IntelligenceDetailModel]:
        query = self.db.query(self.model)

        if source_id:
            query = query.filter(self.model.source_id == source_id)
        if keyword:
            query = query.filter(
                or_(
                    self.model.title.ilike(f"%{keyword}%"),
                    self.model.content.ilike(f"%{keyword}%"),
                )
            )
        if start_date:
            query = query.filter(self.model.collected_at >= start_date)
        if end_date:
            query = query.filter(self.model.collected_at <= end_date)

        return query.order_by(self.model.collected_at.desc()).offset(skip).limit(limit).all()

    def exists_by_dedup_key(self, dedup_key: str) -> bool:
        return self.db.query(self.model).filter(self.model.deduplication_key == dedup_key).first() is not None
