import httpx
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup
import re

from bis.models.models import CollectionTaskModel, IntelligenceDetailModel
from bis.models.schemas import IntelligenceDetailBase
from bis.repositories.repositories import ProxyRepository, UserAgentRepository, IntelligenceRepository, SourceRepository
from bis.core.config import get_settings

settings = get_settings()


class ScraperService:
    def __init__(self, db: Session):
        self.db = db
        self.proxy_repo = ProxyRepository(db)
        self.ua_repo = UserAgentRepository(db)
        self.intel_repo = IntelligenceRepository(db)
        self.source_repo = SourceRepository(db)
        
    async def execute_task(self, task: CollectionTaskModel) -> List[IntelligenceDetailModel]:
        if not task.url:
            return []
        
        items = []
        retry_count = task.retry_count or 2
        
        for attempt in range(retry_count):
            try:
                content = await self.fetch_page(task)
                if content:
                    items = self.parse_content(task, content)
                    if items:
                        break
            except Exception as e:
                if attempt == retry_count - 1:
                    print(f"Task {task.id} failed after {retry_count} attempts: {e}")
                    
        return items
    
    async def fetch_page(self, task: CollectionTaskModel) -> Optional[str]:
        headers = {}
        if task.ua_enabled:
            ua = self.get_random_ua()
            if ua:
                headers["User-Agent"] = ua.ua_string
        
        proxy_url = None
        if task.proxy_enabled:
            proxy = self.get_random_proxy()
            if proxy:
                proxy_url = f"{proxy.protocol}://"
                if proxy.username and proxy.password:
                    proxy_url += f"{proxy.username}:{proxy.password}@"
                proxy_url += f"{proxy.ip}:{proxy.port}"
        
        timeout = task.timeout or 30
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
            response = await client.get(task.url, headers=headers, proxies=proxies)
            response.raise_for_status()
            return response.text
    
    def get_random_ua(self):
        import random
        uas = self.ua_repo.get_enabled()
        return random.choice(uas) if uas else None
    
    def get_random_proxy(self):
        import random
        proxies = self.proxy_repo.get_available()
        return random.choice(proxies) if proxies else None
    
    def parse_content(self, task: CollectionTaskModel, html: str) -> List[IntelligenceDetailModel]:
        items = []
        charset = task.charset or 'utf-8'
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
        except Exception:
            return items
        
        selector = task.list_selector or 'article'
        elements = soup.select(selector)
        
        keywords = [k.lower() for k in (task.keywords or [])]
        
        for element in elements:
            title = self.extract_text(element, task.title_selector)
            content = self.extract_text(element, task.content_selector)
            link = self.extract_link(element, task.link_selector)
            date = self.extract_text(element, task.date_selector)
            
            if not title and not content:
                continue
            
            title_lower = (title or '').lower()
            if keywords and not any(k in title_lower for k in keywords):
                continue
            
            item = IntelligenceDetailModel(
                source_id=task.source_ids[0] if task.source_ids else None,
                title=title,
                content=content,
                raw_data={
                    'link': link,
                    'date': date,
                    'task_id': task.id,
                    'url': task.url,
                },
                collected_at=datetime.utcnow(),
            )
            
            if task.keywords:
                item.keywords = task.keywords
            
            existing = self.intel_repo.exists_by_dedup_key(self._generate_key(task, title, link))
            if not existing:
                items.append(item)
        
        if items:
            self.db.add_all(items)
            self.db.commit()
            for item in items:
                self.db.refresh(item)
        
        return items
    
    def extract_text(self, element, selector: str) -> Optional[str]:
        if not selector:
            return None
        try:
            if selector.startswith('//') or selector.startswith('/'):
                found = element.xpath(selector) if hasattr(element, 'xpath') else None
                if found:
                    return str(found[0]) if found else None
            else:
                selected = element.select(selector)
                if selected:
                    return selected[0].get_text(strip=True)
        except Exception:
            pass
        return None
    
    def extract_link(self, element, selector: str) -> Optional[str]:
        if not selector:
            return None
        try:
            if selector.startswith('//') or selector.startswith('/'):
                found = element.xpath(selector) if hasattr(element, 'xpath') else None
                if found:
                    return str(found[0]) if found else None
            else:
                selected = element.select(selector)
                if selected and selected[0].get('href'):
                    return selected[0]['href']
        except Exception:
            pass
        return None
    
    def _generate_key(self, task: CollectionTaskModel, title: str, link: str) -> str:
        import hashlib
        content = f"{task.id}:{title}:{link}"
        return hashlib.md5(content.encode()).hexdigest()
