import random
from typing import List, Optional
from sqlalchemy.orm import Session

from bis.models.models import UserAgentModel
from bis.models.schemas import UserAgentCreate
from bis.repositories.repositories import UserAgentRepository


class UserAgentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserAgentRepository(db)

    def create(self, data: UserAgentCreate) -> UserAgentModel:
        model = UserAgentModel(
            ua_string=data.ua_string,
            browser=data.browser,
            os=data.os,
        )
        return self.repo.create(model)

    def get_by_id(self, id: str) -> Optional[UserAgentModel]:
        return self.repo.get_by_id(id)

    def get_all(self, skip: int = 0, limit: int = 100) -> List[UserAgentModel]:
        return self.repo.get_all(skip, limit)

    def delete(self, id: str) -> bool:
        return self.repo.delete(id)

    def get_random(self) -> Optional[UserAgentModel]:
        enabled = self.repo.get_enabled()
        if not enabled:
            return None
        return random.choice(enabled)

    def get_random_ua_string(self) -> str:
        ua = self.get_random()
        return ua.ua_string if ua else "Mozilla/5.0 (compatible; BIS/1.0)"
