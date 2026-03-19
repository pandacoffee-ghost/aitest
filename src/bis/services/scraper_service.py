import httpx
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup
from lxml import etree
import re
import base64

from bis.models.models import CollectionTaskModel, IntelligenceDetailModel
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
                result = await self.fetch_page(task)
                if result:
                    html, screenshot = result
                    items = self.parse_content(task, html, screenshot)
                    if items:
                        break
            except Exception as e:
                if attempt == retry_count - 1:
                    print(f"Task {task.id} failed after {retry_count} attempts: {e}")
                    
        return items
    
    async def fetch_page(self, task: CollectionTaskModel) -> Optional[tuple]:
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
        screenshot = None
        
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            proxies = {"http://": proxy_url, "https://": proxy_url} if proxy_url else None
            response = await client.get(task.url, headers=headers, proxies=proxies)
            response.raise_for_status()
            html = response.text
            
            if task.do_screenshot:
                try:
                    screenshot = await self.take_screenshot(task.url, proxy_url, headers)
                except Exception as e:
                    print(f"Screenshot failed: {e}")
            
            return html, screenshot
    
    async def take_screenshot(self, url: str, proxy_url: str, headers: dict) -> Optional[str]:
        return None
    
    def get_random_ua(self):
        import random
        uas = self.ua_repo.get_enabled()
        return random.choice(uas) if uas else None
    
    def get_random_proxy(self):
        import random
        proxies = self.proxy_repo.get_available()
        return random.choice(proxies) if proxies else None
    
    def parse_content(self, task: CollectionTaskModel, html: str, screenshot: Optional[str] = None) -> List[IntelligenceDetailModel]:
        items = []
        
        try:
            soup = BeautifulSoup(html, 'lxml')
        except Exception:
            soup = BeautifulSoup(html, 'html.parser')
        
        selector = task.list_selector or 'article'
        selector_type = task.list_selector_type or 'css'
        
        elements = self.select_elements(soup, selector, selector_type)
        
        keywords = [k.lower() for k in (task.keywords or [])]
        
        for element in elements:
            title = self.extract_text(element, task.title_selector, task.title_selector_type)
            content = self.extract_text(element, task.content_selector, task.content_selector_type)
            link = self.extract_link(element, task.link_selector, task.link_selector_type)
            date = self.extract_text(element, task.date_selector, task.date_selector_type)
            
            if not title and not content:
                continue
            
            title_lower = (title or '').lower()
            if keywords and not any(k in title_lower for k in keywords):
                continue
            
            raw_data = {
                'link': link,
                'date': date,
                'task_id': task.id,
                'url': task.url,
            }
            
            if screenshot:
                raw_data['screenshot'] = screenshot
            
            item = IntelligenceDetailModel(
                source_id=task.source_ids[0] if task.source_ids else None,
                title=title,
                content=content,
                raw_data=raw_data,
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
    
    def select_elements(self, soup, selector: str, selector_type: str) -> List:
        if not selector:
            return []
        
        try:
            if selector_type == 'xpath':
                return soup.xpath(selector) if hasattr(soup, 'xpath') else []
            elif selector_type == 'regex':
                return []
            else:
                return soup.select(selector)
        except Exception:
            return []
    
    def extract_text(self, element, selector: str, selector_type: str = 'css') -> Optional[str]:
        if not selector:
            return None
        try:
            if selector_type == 'xpath':
                if hasattr(element, 'xpath'):
                    found = element.xpath(selector)
                    if found:
                        return str(found[0]) if isinstance(found, list) else str(found)
            elif selector_type == 'regex':
                return None
            else:
                selected = element.select(selector)
                if selected:
                    return selected[0].get_text(strip=True)
        except Exception:
            pass
        return None
    
    def extract_link(self, element, selector: str, selector_type: str = 'css') -> Optional[str]:
        if not selector:
            return None
        try:
            if selector_type == 'xpath':
                if hasattr(element, 'xpath'):
                    found = element.xpath(selector)
                    if found and isinstance(found, list) and len(found) > 0:
                        href = found[0].get('href') if hasattr(found[0], 'get') else str(found[0])
                        return href
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
