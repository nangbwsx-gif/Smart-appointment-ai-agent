"""
Web / API 路由层测试

特点：不依赖真实 LLM 与真实数据库
- LLM：模块导入时 api/chat_handler.py 会构造 agent，需要凭据才能导入成功，
  这里用假的占位凭据（不会产生网络请求）；真正调用 LLM 的接口全部 mock 掉
- 数据库：需要数据库的用例通过 monkeypatch SessionManager 强制指向临时库，
  避免污染 data/smart_appointment.db
"""
import importlib
import os

import pytest
from fastapi.testclient import TestClient

# 导入 app 之前必须先放好占位凭据：config/model_provider.py 的 create_chat_model
# 在没有 api_key 时会直接抛 OpenAIError，导致 import app 失败
_FAKE_ENV = {
    "MODEL_PROVIDER": "openai-compatible",
    "LLM_API_KEY": "ci-dummy-key",
    "LLM_BASE_URL": "http://127.0.0.1:9/v1",
    "LLM_MODEL": "dummy-model",
    "EMBEDDING_API_KEY": "ci-dummy-key",
    "EMBEDDING_BASE_URL": "http://127.0.0.1:9/v1",
}


@pytest.fixture(scope="module")
def client():
    """FastAPI 测试客户端（不进 with 上下文，避免触发 startup 的真实初始化）"""
    saved = {key: os.environ.get(key) for key in _FAKE_ENV}
    os.environ.update(_FAKE_ENV)
    try:
        app_module = importlib.import_module("app")
        yield TestClient(app_module.app)
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """把所有数据库连接指向临时库，测试结束后自动丢弃"""
    from db.base.session_manager import SessionManager

    db_file = (tmp_path / "test.db").as_posix()
    original_init = SessionManager.__init__

    def patched_init(self, db_path=None):
        original_init(self, f"sqlite:///{db_file}")

    monkeypatch.setattr(SessionManager, "__init__", patched_init)
    return db_file


# ---------------------------------------------------------------- 页面渲染

def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<html" in response.text.lower()


@pytest.mark.parametrize("path", ["/user_behavior", "/user_behavior_analysis"])
def test_static_pages(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert "<html" in response.text.lower()


def test_admin_dashboard_page(client):
    """模板缺失曾导致 /admin 直接 500"""
    response = client.get("/admin")
    assert response.status_code == 200
    assert "<html" in response.text.lower()


def test_database_admin_page(client):
    """模板缺失曾导致 /admin/database 直接 500"""
    response = client.get("/admin/database")
    assert response.status_code == 200
    assert "<html" in response.text.lower()


# ---------------------------------------------------------------- 聊天接口

def test_chat_stream_requires_message(client):
    response = client.post("/chat/stream", json={})
    assert response.status_code == 422


def test_chat_stream_returns_mocked_tokens(client, monkeypatch):
    async def fake_stream(message, state=None, context=None):
        yield "你好"
        yield "，很高兴见到你"

    monkeypatch.setattr("web.routes.ProcessUserInput_stream", fake_stream)

    response = client.post("/chat/stream", json={"message": "你好"})
    assert response.status_code == 200
    assert response.text == "你好，很高兴见到你"


def test_chat_endpoint_returns_mocked_tokens(client, monkeypatch):
    async def fake_stream(message, state=None, context=None):
        yield "测试回复"

    monkeypatch.setattr("web.routes.ProcessUserInput_stream", fake_stream)

    response = client.post("/chat", json={"message": "你好"})
    assert response.status_code == 200
    assert response.text == "测试回复"


# ---------------------------------------------------------------- 数据页面

def test_technician_page(client, monkeypatch):
    async def fake_get_all_technicians():
        return [{"id": 1, "name": "张三", "gender": "男", "strength": "全身推拿"}]

    monkeypatch.setattr("api.technician.get_all_technicians", fake_get_all_technicians)

    response = client.get("/technician")
    assert response.status_code == 200


def test_technician_schedule_page(client, monkeypatch):
    async def fake_schedules():
        return [
            {
                "technician_id": 1,
                "technician_name": "张三",
                "busy_periods": [{"start_time": "09:00", "end_time": "10:00"}],
            }
        ]

    monkeypatch.setattr("api.technician.get_all_technicians_schedule_today", fake_schedules)

    response = client.get("/technician_schedule")
    assert response.status_code == 200


def test_knowledge_page(client, monkeypatch):
    async def fake_get_all_knowledge():
        return {
            "documents": [{"id": 1, "question": "价格", "answer": "120元"}],
            "categories": ["价格"],
            "total_count": 1,
            "status": "success",
        }

    monkeypatch.setattr("api.knowledge.get_all_knowledge", fake_get_all_knowledge)

    response = client.get("/knowledge")
    assert response.status_code == 200


# ---------------------------------------------------------------- 数据接口

def test_technicians_api_uses_isolated_database(client, tmp_db):
    response = client.get("/api/technicians/")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 10
    assert {"id", "name"} <= set(body[0])


def test_task_classify_rejects_unknown_payload(client):
    """请求体字段名是 text，缺失时由 pydantic 校验返回 422"""
    response = client.post("/api/task/classify", json={})
    assert response.status_code == 422


def test_knowledge_search_endpoint(client, tmp_db, monkeypatch):
    """知识库搜索会触发 embedding，mock 掉 service 的初始化与检索"""
    from services.knowledge_service import KnowledgeService

    async def fake_initialize(self):
        self.initialized = True

    async def fake_search(self, query, top_k=3, category=None):
        return [{"id": 1, "question": query, "answer": "答案", "score": 0.9}]

    monkeypatch.setattr(KnowledgeService, "initialize", fake_initialize)
    monkeypatch.setattr(KnowledgeService, "search", fake_search)

    response = client.post("/api/knowledge/search", json={"query": "价格"})
    assert response.status_code == 200
    assert response.json()["count"] == 1
