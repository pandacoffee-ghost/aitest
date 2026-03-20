from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from bis.core.config import get_settings
from bis.core.logging import setup_logging
from bis.core.database import init_db
from bis.core.task_runner import shutdown_task_runner
from bis.api import sources, proxies, user_agents, tasks, intelligence, rules

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.app.debug)
    init_db()
    yield
    shutdown_task_runner()


app = FastAPI(
    title="Business Intelligence System",
    description="业务情报系统 - 配置情报源、生成情报详情、代理池和UA池管理",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sources.router)
app.include_router(proxies.router)
app.include_router(user_agents.router)
app.include_router(tasks.router)
app.include_router(intelligence.router)
app.include_router(rules.router)


with open("src/bis/templates/index.html", "r", encoding="utf-8") as f:
    HTML_CONTENT = f.read()


@app.get("/")
def root():
    return HTMLResponse(content=HTML_CONTENT, status_code=200)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "bis.main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.debug,
    )
