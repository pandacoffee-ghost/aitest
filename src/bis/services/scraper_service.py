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
        url, headers, cookies = self.build_request_options(task)
        if not url:
            return None

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
        html = await self.fetch_html(
            url,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            proxy_url=proxy_url,
        )
            
        if task.do_screenshot:
            try:
                screenshot = await self.take_screenshot(url, proxy_url, headers)
            except Exception as e:
                print(f"Screenshot failed: {e}")
        
        return html, screenshot

    async def fetch_html(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        proxy_url: Optional[str] = None,
    ) -> str:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            proxies = {"http://": proxy_url, "https://": proxy_url} if proxy_url else None
            response = await client.get(url, headers=headers or {}, cookies=cookies or {}, proxies=proxies)
            response.raise_for_status()
            return response.text

    def build_request_options(self, task: CollectionTaskModel) -> tuple[Optional[str], Dict[str, str], Dict[str, str]]:
        headers: Dict[str, str] = {}
        cookies: Dict[str, str] = {}
        url = task.url

        source = None
        if task.source_ids:
            source = self.source_repo.get_by_id(task.source_ids[0])

        if source:
            headers.update(source.headers or {})
            cookies.update(source.cookies or {})
            url = url or source.url

        return url, headers, cookies
    
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
        items, _ = self.parse_content_with_stats(task, html, screenshot)
        return items

    def parse_content_with_stats(
        self,
        task: CollectionTaskModel,
        html: str,
        screenshot: Optional[str] = None,
    ) -> tuple[List[IntelligenceDetailModel], Dict[str, int]]:
        items = []

        try:
            soup = BeautifulSoup(html, 'lxml')
        except Exception:
            soup = BeautifulSoup(html, 'html.parser')
        
        rule = task.rule
        selector = task.list_selector or (rule.list_selector if rule else None) or 'article'
        selector_type = task.list_selector_type or (rule.list_selector_type if rule else None) or 'css'
        
        elements = self.select_elements(soup, selector, selector_type)
        stats = {
            "matched_blocks": len(elements),
            "empty_title_count": 0,
            "empty_content_count": 0,
            "title_hits": 0,
            "content_hits": 0,
            "link_hits": 0,
            "date_hits": 0,
            "problem_samples": [],
        }
        
        keywords = [k.lower() for k in (task.keywords or [])]
        
        for element in elements:
            title = self.extract_text(
                element,
                task.title_selector or (rule.title_selector if rule else None),
                task.title_selector_type or (rule.title_selector_type if rule else 'css'),
            )
            content = self.extract_text(
                element,
                task.content_selector or (rule.content_selector if rule else None),
                task.content_selector_type or (rule.content_selector_type if rule else 'css'),
            )
            link = self.extract_link(
                element,
                task.link_selector or (rule.link_selector if rule else None),
                task.link_selector_type or (rule.link_selector_type if rule else 'css'),
            )
            date = self.extract_text(
                element,
                task.date_selector or (rule.date_selector if rule else None),
                task.date_selector_type or (rule.date_selector_type if rule else 'css'),
            )
            if not title:
                stats["empty_title_count"] += 1
            else:
                stats["title_hits"] += 1
            if not content:
                stats["empty_content_count"] += 1
            else:
                stats["content_hits"] += 1
            if link:
                stats["link_hits"] += 1
            if date:
                stats["date_hits"] += 1
            missing_fields = []
            if not title:
                missing_fields.append("title")
            if not content:
                missing_fields.append("content")
            if not link:
                missing_fields.append("link")
            if missing_fields and len(stats["problem_samples"]) < 5:
                stats["problem_samples"].append(
                    {
                        "missing_fields": missing_fields,
                        "text_preview": element.get_text(" ", strip=True)[:120],
                    }
                )
            
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
            item.deduplication_key = self._generate_key(task, title, link)
            
            if task.keywords:
                item.keywords = task.keywords
            
            existing = self.intel_repo.exists_by_dedup_key(item.deduplication_key)
            if not existing:
                items.append(item)
        
        if items:
            self.db.add_all(items)
            self.db.commit()
            for item in items:
                self.db.refresh(item)

        return items, stats
    
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
