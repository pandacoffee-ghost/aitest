from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from bis.core.database import get_db
from bis.models.schemas import UserAgentCreate, UserAgent
from bis.services.ua_service import UserAgentService

router = APIRouter(prefix="/api/v1/user-agents", tags=["user-agents"])

BUILTIN_UAS = {
    "pc_chrome": [
        {"ua_string": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "browser": "Chrome", "os": "Windows 10"},
        {"ua_string": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36", "browser": "Chrome", "os": "Windows 10"},
        {"ua_string": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "browser": "Chrome", "os": "macOS"},
        {"ua_string": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "browser": "Chrome", "os": "Linux"},
        {"ua_string": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0", "browser": "Firefox", "os": "Windows 10"},
        {"ua_string": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15", "browser": "Safari", "os": "macOS"},
        {"ua_string": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0", "browser": "Edge", "os": "Windows 10"},
    ],
    "pc_firefox": [
        {"ua_string": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0", "browser": "Firefox", "os": "Windows 10"},
        {"ua_string": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0", "browser": "Firefox", "os": "macOS"},
        {"ua_string": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0", "browser": "Firefox", "os": "Ubuntu"},
    ],
    "mobile_android": [
        {"ua_string": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36", "browser": "Chrome", "os": "Android 14"},
        {"ua_string": "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36", "browser": "Chrome", "os": "Android 13"},
        {"ua_string": "Mozilla/5.0 (Linux; Android 12; SM-A136B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36", "browser": "Chrome", "os": "Android 12"},
    ],
    "mobile_ios": [
        {"ua_string": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1", "browser": "Safari", "os": "iOS 17"},
        {"ua_string": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1", "browser": "Safari", "os": "iOS 16"},
        {"ua_string": "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1", "browser": "Safari", "os": "iPadOS 17"},
    ],
    "mini_program": [
        {"ua_string": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.47 NetType/WIFI Language/zh_CN", "browser": "WeChat", "os": "iOS"},
        {"ua_string": "Mozilla/5.0 (Linux; Android 14; Pixel 8 Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0.6099.144 Mobile Safari/537.36 MicroMessenger/8.0.47.2048 NetType/WIFI Language/zh_CN", "browser": "WeChat", "os": "Android"},
        {"ua_string": "Mozilla/5.0 (Linux; Android 13; HUAWEI-AL00) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0.6099.144 Mobile Safari/537.36 AlipayServer/1.0.2", "browser": "Alipay", "os": "Android"},
        {"ua_string": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.47 NetType/WIFI Language/zh_CN", "browser": "WeChat", "os": "iOS"},
    ],
    "app_ios": [
        {"ua_string": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148", "browser": "iOS App", "os": "iOS"},
        {"ua_string": "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148", "browser": "iOS App", "os": "iPadOS"},
    ],
    "app_android": [
        {"ua_string": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Mobile", "browser": "Android App", "os": "Android"},
        {"ua_string": "Mozilla/5.0 (Linux; Android 13; SM-A136B) AppleWebKit/537.36 (KHTML, like Gecko) Mobile", "browser": "Android App", "os": "Android"},
    ],
}


@router.post("", response_model=UserAgent, status_code=status.HTTP_201_CREATED)
def create_ua(data: UserAgentCreate, db: Session = Depends(get_db)):
    service = UserAgentService(db)
    return service.create(data)


@router.get("", response_model=List[UserAgent])
def list_uas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    service = UserAgentService(db)
    return service.get_all(skip, limit)


@router.get("/categories", response_model=dict)
def list_ua_categories():
    return {k: len(v) for k, v in BUILTIN_UAS.items()}


@router.get("/builtin/{category}", response_model=List[dict])
def get_builtin_uas_by_category(category: str):
    if category not in BUILTIN_UAS:
        raise HTTPException(status_code=404, detail="Category not found")
    return BUILTIN_UAS[category]


@router.get("/random", response_model=UserAgent)
def get_random_ua(db: Session = Depends(get_db)):
    service = UserAgentService(db)
    ua = service.get_random()
    if not ua:
        raise HTTPException(status_code=404, detail="No enabled User-Agent found")
    return ua


@router.get("/{ua_id}", response_model=UserAgent)
def get_ua(ua_id: str, db: Session = Depends(get_db)):
    service = UserAgentService(db)
    ua = service.get_by_id(ua_id)
    if not ua:
        raise HTTPException(status_code=404, detail="User-Agent not found")
    return ua


@router.delete("/{ua_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ua(ua_id: str, db: Session = Depends(get_db)):
    service = UserAgentService(db)
    if not service.delete(ua_id):
        raise HTTPException(status_code=404, detail="User-Agent not found")


@router.post("/batch", response_model=List[UserAgent], status_code=status.HTTP_201_CREATED)
def create_uas_batch(data: List[UserAgentCreate], db: Session = Depends(get_db)):
    service = UserAgentService(db)
    results = []
    for item in data:
        try:
            results.append(service.create(item))
        except Exception:
            continue
    return results


@router.post("/import/{category}", response_model=List[UserAgent], status_code=status.HTTP_201_CREATED)
def import_builtin_uas(category: str, db: Session = Depends(get_db)):
    if category not in BUILTIN_UAS:
        raise HTTPException(status_code=404, detail="Category not found")
    service = UserAgentService(db)
    results = []
    for item in BUILTIN_UAS[category]:
        try:
            results.append(service.create(UserAgentCreate(**item)))
        except Exception:
            continue
    return results
