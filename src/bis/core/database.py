from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from bis.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database.url,
    echo=settings.database.echo,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from bis.models.models import Base
    Base.metadata.create_all(bind=engine)
