from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from bis.core.database import get_db
from bis.main import app
from bis.models.models import Base, CollectionRuleModel, CollectionTaskModel, IntelligenceDetailModel, IntelligenceSourceModel, TaskStatus
from bis.services.scraper_service import ScraperService
from bis.services.task_service import TaskService


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_task(db_session):
    task = CollectionTaskModel(
        name="demo task",
        url="https://example.com",
        list_selector="article",
        title_selector="h2",
        content_selector="p",
        status=TaskStatus.PENDING.value,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


def test_successful_execution_creates_run_record_and_dedup_key(db_session, monkeypatch):
    task = create_task(db_session)
    service = TaskService(db_session)

    async def fake_execute_task(task_model):
        return [
            IntelligenceDetailModel(
                source_id=None,
                title="Signal",
                content="Useful content",
                deduplication_key="abc123",
                collected_at=datetime.utcnow(),
            )
        ]

    scraper = ScraperService(db_session)
    monkeypatch.setattr(scraper, "execute_task", fake_execute_task)
    result = service.execute_task(task.id, scraper)

    assert result.status == TaskStatus.COMPLETED.value
    assert result.latest_run is not None
    assert result.latest_run.status == "completed"
    assert result.latest_run.items_fetched == 1
    assert result.latest_run.items_collected == 1
    stored = db_session.query(IntelligenceDetailModel).all()
    assert len(stored) == 1
    assert stored[0].deduplication_key == "abc123"


def test_failed_execution_marks_task_failed(db_session, monkeypatch):
    task = create_task(db_session)
    service = TaskService(db_session)
    scraper = ScraperService(db_session)

    async def fake_execute_task(task_model):
        raise RuntimeError("boom")

    monkeypatch.setattr(scraper, "execute_task", fake_execute_task)

    result = service.execute_task(task.id, scraper)

    assert result.status == TaskStatus.FAILED.value
    assert result.latest_run is not None
    assert result.latest_run.status == "failed"
    assert "boom" in result.latest_run.error_message


def test_task_run_history_endpoint_returns_runs(client, db_session, monkeypatch):
    task = create_task(db_session)
    service = TaskService(db_session)
    scraper = ScraperService(db_session)

    async def fake_execute_task(task_model):
        return []

    monkeypatch.setattr(scraper, "execute_task", fake_execute_task)
    service.execute_task(task.id, scraper)

    response = client.get(f"/api/v1/tasks/{task.id}/runs")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["task_id"] == task.id


def test_task_run_summary_endpoint_returns_latest_metrics(client, db_session, monkeypatch):
    task = create_task(db_session)
    service = TaskService(db_session)
    scraper = ScraperService(db_session)

    async def fake_execute_task(task_model):
        return [
            IntelligenceDetailModel(
                title="Summary Signal",
                content="Summary content",
                deduplication_key="summary-key",
                collected_at=datetime.utcnow(),
            )
        ]

    monkeypatch.setattr(scraper, "execute_task", fake_execute_task)
    service.execute_task(task.id, scraper)

    response = client.get(f"/api/v1/tasks/{task.id}/run-summary")

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == task.id
    assert body["latest_status"] == "completed"
    assert body["items_fetched"] == 1
    assert body["items_collected"] == 1


def test_run_endpoint_queues_task_and_submits_background_job(client, db_session, monkeypatch):
    task = create_task(db_session)
    submitted = {}

    def fake_submit(task_id):
        submitted["task_id"] = task_id

    monkeypatch.setattr("bis.api.tasks.submit_task", fake_submit)

    response = client.post(f"/api/v1/tasks/{task.id}/run")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == TaskStatus.QUEUED.value
    assert submitted["task_id"] == task.id


def test_invalid_intelligence_date_returns_400(client):
    response = client.get("/api/v1/intelligence?start_date=not-a-date")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid start_date format. Use ISO 8601."


def test_task_can_use_bound_rule_selectors(db_session):
    rule = CollectionRuleModel(
        name="article rule",
        list_selector="article",
        title_selector="h2",
        content_selector="p",
        link_selector="a",
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)

    task = CollectionTaskModel(
        name="rule driven task",
        url="https://example.com",
        rule_id=rule.id,
        status=TaskStatus.PENDING.value,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    scraper = ScraperService(db_session)
    html = """
    <html>
      <body>
        <article>
          <h2>Rule Title</h2>
          <p>Rule Content</p>
          <a href="https://example.com/item">Read</a>
        </article>
      </body>
    </html>
    """

    items = scraper.parse_content(task, html)

    assert len(items) == 1
    assert items[0].title == "Rule Title"
    assert items[0].content == "Rule Content"


def test_task_uses_source_request_configuration(db_session):
    source = IntelligenceSourceModel(
        name="source",
        url="https://example.com/feed",
        headers={"X-Source": "alpha"},
        cookies={"session": "cookie123"},
        enabled=True,
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    task = CollectionTaskModel(
        name="source backed task",
        source_ids=[source.id],
        status=TaskStatus.PENDING.value,
        ua_enabled=False,
        proxy_enabled=False,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    scraper = ScraperService(db_session)

    url, headers, cookies = scraper.build_request_options(task)

    assert url == "https://example.com/feed"
    assert headers["X-Source"] == "alpha"
    assert cookies["session"] == "cookie123"


def test_rule_preview_endpoint_parses_raw_html(client):
    response = client.post(
        "/api/v1/rules/preview",
        json={
            "name": "preview rule",
            "list_selector": "article",
            "title_selector": "h2",
            "content_selector": "p",
            "link_selector": "a",
            "raw_html": """
                <html><body>
                  <article>
                    <h2>Preview Title</h2>
                    <p>Preview Content</p>
                    <a href='https://example.com/preview'>Read</a>
                  </article>
                </body></html>
            """,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["matched_blocks"] == 1
    assert body["empty_title_count"] == 0
    assert body["empty_content_count"] == 0
    assert body["items"][0]["title"] == "Preview Title"
    assert body["items"][0]["content"] == "Preview Content"
    assert body["items"][0]["raw_data"]["link"] == "https://example.com/preview"


def test_rule_preview_endpoint_can_fetch_from_url(client, monkeypatch):
    async def fake_fetch_url(url, headers=None, cookies=None, timeout=30, proxy_url=None):
        return """
            <html><body>
              <article>
                <h2>Fetched Title</h2>
                <p>Fetched Content</p>
                <a href='https://example.com/fetched'>Read</a>
              </article>
            </body></html>
        """

    monkeypatch.setattr("bis.services.scraper_service.ScraperService.fetch_html", fake_fetch_url)

    response = client.post(
        "/api/v1/rules/preview",
        json={
            "name": "preview by url",
            "url": "https://example.com/list",
            "list_selector": "article",
            "title_selector": "h2",
            "content_selector": "p",
            "link_selector": "a",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["title"] == "Fetched Title"


def test_task_detail_includes_bound_rule(client, db_session):
    rule = CollectionRuleModel(name="detail rule", list_selector="article")
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)

    task = CollectionTaskModel(
        name="task with rule",
        rule_id=rule.id,
        status=TaskStatus.PENDING.value,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    response = client.get(f"/api/v1/tasks/{task.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["rule_id"] == rule.id
    assert body["rule"]["id"] == rule.id
    assert body["rule"]["name"] == "detail rule"


def test_task_update_changes_runtime_behavior(client, db_session):
    original_rule = CollectionRuleModel(
        name="old rule",
        list_selector="article",
        title_selector="h2",
        content_selector="p",
    )
    new_rule = CollectionRuleModel(
        name="new rule",
        list_selector=".item",
        title_selector=".headline",
        content_selector=".body",
    )
    db_session.add_all([original_rule, new_rule])
    db_session.commit()
    db_session.refresh(original_rule)
    db_session.refresh(new_rule)

    task = CollectionTaskModel(
        name="editable task",
        rule_id=original_rule.id,
        status=TaskStatus.PENDING.value,
        timeout=30,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    response = client.put(
        f"/api/v1/tasks/{task.id}",
        json={
            "name": "edited task",
            "rule_id": new_rule.id,
            "timeout": 45,
            "keywords": ["brand"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "edited task"
    assert body["rule_id"] == new_rule.id
    assert body["timeout"] == 45
    assert body["keywords"] == ["brand"]
    assert body["rule"]["name"] == "new rule"

    db_session.refresh(task)
    scraper = ScraperService(db_session)
    html = """
    <html><body>
      <div class="item">
        <div class="headline">Brand Watch</div>
        <div class="body">Updated body</div>
      </div>
    </body></html>
    """
    items = scraper.parse_content(task, html)

    assert len(items) == 1
    assert items[0].title == "Brand Watch"


def test_batch_pause_updates_multiple_running_tasks(client, db_session):
    tasks = [
        CollectionTaskModel(name="run-a", status=TaskStatus.RUNNING.value),
        CollectionTaskModel(name="run-b", status=TaskStatus.RUNNING.value),
    ]
    db_session.add_all(tasks)
    db_session.commit()
    for task in tasks:
        db_session.refresh(task)

    response = client.post(
        "/api/v1/tasks/batch-pause",
        json={"task_ids": [tasks[0].id, tasks[1].id]},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {item["status"] for item in body} == {TaskStatus.PAUSED.value}


def test_batch_resume_updates_multiple_paused_tasks(client, db_session):
    tasks = [
        CollectionTaskModel(name="pause-a", status=TaskStatus.PAUSED.value),
        CollectionTaskModel(name="pause-b", status=TaskStatus.PAUSED.value),
    ]
    db_session.add_all(tasks)
    db_session.commit()
    for task in tasks:
        db_session.refresh(task)

    response = client.post(
        "/api/v1/tasks/batch-resume",
        json={"task_ids": [tasks[0].id, tasks[1].id]},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {item["status"] for item in body} == {TaskStatus.PENDING.value}


def test_batch_run_queues_multiple_tasks(client, db_session, monkeypatch):
    tasks = [
        CollectionTaskModel(name="ready-a", status=TaskStatus.PENDING.value),
        CollectionTaskModel(name="ready-b", status=TaskStatus.PENDING.value),
    ]
    db_session.add_all(tasks)
    db_session.commit()
    for task in tasks:
        db_session.refresh(task)

    submitted = []

    def fake_submit(task_id):
        submitted.append(task_id)

    monkeypatch.setattr("bis.api.tasks.submit_task", fake_submit)

    response = client.post(
        "/api/v1/tasks/batch-run",
        json={"task_ids": [tasks[0].id, tasks[1].id]},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {item["status"] for item in body} == {TaskStatus.QUEUED.value}
    assert set(submitted) == {tasks[0].id, tasks[1].id}


def test_batch_cancel_updates_multiple_tasks(client, db_session):
    tasks = [
        CollectionTaskModel(name="cancel-a", status=TaskStatus.PENDING.value),
        CollectionTaskModel(name="cancel-b", status=TaskStatus.RUNNING.value),
    ]
    db_session.add_all(tasks)
    db_session.commit()
    for task in tasks:
        db_session.refresh(task)

    response = client.post(
        "/api/v1/tasks/batch-cancel",
        json={"task_ids": [tasks[0].id, tasks[1].id]},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {item["status"] for item in body} == {TaskStatus.CANCELLED.value}


def test_batch_bind_rule_updates_multiple_tasks(client, db_session):
    rule = CollectionRuleModel(name="batch rule")
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)

    tasks = [
        CollectionTaskModel(name="task-a", status=TaskStatus.PENDING.value),
        CollectionTaskModel(name="task-b", status=TaskStatus.PENDING.value),
    ]
    db_session.add_all(tasks)
    db_session.commit()
    for task in tasks:
        db_session.refresh(task)

    response = client.post(
        "/api/v1/tasks/bind-rule",
        json={"task_ids": [tasks[0].id, tasks[1].id], "rule_id": rule.id},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert {item["rule_id"] for item in body} == {rule.id}


def test_task_list_supports_status_and_rule_filters(client, db_session):
    rule = CollectionRuleModel(name="filter rule")
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)

    matching = CollectionTaskModel(
        name="matching",
        status=TaskStatus.QUEUED.value,
        rule_id=rule.id,
    )
    other = CollectionTaskModel(
        name="other",
        status=TaskStatus.PENDING.value,
    )
    db_session.add_all([matching, other])
    db_session.commit()

    response = client.get(f"/api/v1/tasks?status=queued&rule_id={rule.id}")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "matching"


def test_task_list_supports_name_search(client, db_session):
    db_session.add_all(
        [
            CollectionTaskModel(name="Competitor Monitor", status=TaskStatus.PENDING.value),
            CollectionTaskModel(name="News Digest", status=TaskStatus.PENDING.value),
        ]
    )
    db_session.commit()

    response = client.get("/api/v1/tasks?q=competitor")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Competitor Monitor"


def test_rule_list_supports_name_search(client, db_session):
    db_session.add_all(
        [
            CollectionRuleModel(name="Homepage Rule"),
            CollectionRuleModel(name="RSS Rule"),
        ]
    )
    db_session.commit()

    response = client.get("/api/v1/rules?q=home")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Homepage Rule"


def test_rule_can_be_disabled_and_enabled(client, db_session):
    rule = CollectionRuleModel(name="toggle rule", enabled=True)
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)

    disable_response = client.post(f"/api/v1/rules/{rule.id}/disable")
    assert disable_response.status_code == 200
    assert disable_response.json()["enabled"] is False

    enable_response = client.post(f"/api/v1/rules/{rule.id}/enable")
    assert enable_response.status_code == 200
    assert enable_response.json()["enabled"] is True
