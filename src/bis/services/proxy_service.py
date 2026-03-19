import httpx
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from bis.models.models import ProxyModel
from bis.models.schemas import ProxyCreate
from bis.repositories.repositories import ProxyRepository
from bis.core.config import get_settings
from loguru import logger

settings = get_settings()


class ProxyService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProxyRepository(db)
        self.config = settings.proxy

    def create(self, data: ProxyCreate) -> ProxyModel:
        existing = self.repo.get_by_ip_port(data.ip, data.port)
        if existing:
            raise ValueError(f"Proxy {data.ip}:{data.port} already exists")

        model = ProxyModel(
            ip=data.ip,
            port=data.port,
            protocol=data.protocol.value,
            username=data.username,
            password=data.password,
        )
        return self.repo.create(model)

    def get_by_id(self, id: str) -> Optional[ProxyModel]:
        return self.repo.get_by_id(id)

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ProxyModel]:
        return self.repo.get_all(skip, limit)

    def get_available(self) -> List[ProxyModel]:
        return self.repo.get_available()

    def delete(self, id: str) -> bool:
        return self.repo.delete(id)

    async def test_proxy(self, id: str) -> dict:
        proxy = self.repo.get_by_id(id)
        if not proxy:
            return {"success": False, "error": "Proxy not found"}

        proxy_url = f"{proxy.protocol}://"
        if proxy.username and proxy.password:
            proxy_url += f"{proxy.username}:{proxy.password}@"
        proxy_url += f"{proxy.ip}:{proxy.port}"

        proxies = {"http": proxy_url, "https": proxy_url}

        try:
            start_time = datetime.utcnow()
            async with httpx.AsyncClient(timeout=settings.scraper.proxy_test_timeout) as client:
                response = await client.get(settings.proxy.test_url, proxies=proxies)
                elapsed = (datetime.utcnow() - start_time).total_seconds()

            if response.status_code == 200:
                proxy.quality_score = max(0.1, 1.0 - (elapsed / 10))
                proxy.last_tested_at = datetime.utcnow()
                proxy.failure_count = 0
                self.repo.update(proxy)
                return {"success": True, "response_time": elapsed, "quality_score": proxy.quality_score}
            else:
                proxy.failure_count += 1
                self._handle_failure(proxy)
                return {"success": False, "status_code": response.status_code}
        except Exception as e:
            proxy.failure_count += 1
            self._handle_failure(proxy)
            return {"success": False, "error": str(e)}

    def _handle_failure(self, proxy: ProxyModel) -> None:
        if proxy.failure_count >= self.config.max_failure_count:
            proxy.enabled = False
            logger.warning(f"Proxy {proxy.id} disabled due to repeated failures")
        proxy.last_tested_at = datetime.utcnow()
        self.repo.update(proxy)

    def get_random_available(self) -> Optional[ProxyModel]:
        available = self.get_available()
        if not available:
            return None
        import random
        return random.choice(available)
