from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseModel):
    url: str = "sqlite:///./bis.db"
    echo: bool = False


class RedisConfig(BaseModel):
    url: str = "redis://localhost:6379/0"
    enabled: bool = False


class SchedulerConfig(BaseModel):
    timezone: str = "UTC"
    max_instances: int = 3


class ScraperConfig(BaseModel):
    default_timeout: int = 30
    max_retries: int = 3
    proxy_test_timeout: int = 5


class ProxyConfig(BaseModel):
    max_failure_count: int = 3
    quality_threshold: float = 0.5
    test_url: str = "http://httpbin.org/ip"


class TaskConfig(BaseModel):
    default_timeout: int = 300
    default_retry_count: int = 3
    max_concurrent: int = 10


class IntelligenceConfig(BaseModel):
    deduplication_enabled: bool = True
    summary_max_length: int = 500


class AppConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False


class Settings(BaseSettings):
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    scheduler: SchedulerConfig = SchedulerConfig()
    scraper: ScraperConfig = ScraperConfig()
    proxy: ProxyConfig = ProxyConfig()
    task: TaskConfig = TaskConfig()
    intelligence: IntelligenceConfig = IntelligenceConfig()
    app: AppConfig = AppConfig()

    @classmethod
    def from_yaml(cls, config_path: Optional[str] = None) -> "Settings":
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent.parent / "config.yaml"
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            return cls()

        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)

        return cls(**config_data)


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings.from_yaml()
    return _settings
