import importlib
import io
import os
import sys
from pathlib import Path
from typing import Dict

import jwt
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _make_token(subject: str) -> str:
    return jwt.encode({"sub": subject, "exp": 4102444800}, "test-secret", algorithm="HS256")


def _auth_header(subject: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {_make_token(subject)}"}


def _client() -> TestClient:
    os.environ["AUTH_ENABLED"] = "true"
    os.environ["JWT_SECRET"] = "test-secret"
    os.environ["SECURITY_PRODUCTION_MODE"] = "true"
    os.environ["ENABLE_DEPRECATED_ENDPOINTS"] = "false"
    module = importlib.import_module("api.search_api")
    return TestClient(module.app)


def test_auth_required_on_chat_endpoint():
    client = _client()
    res = client.post("/ask", json={"q": "hi", "analysis_id": "abc"})
    assert res.status_code == 401


def test_session_upload_ask_flow_with_ownership(monkeypatch):
    # Lazy import for monkeypatching route-level symbols.
    erd_module = importlib.import_module("api.erd_processor")
    search_module = importlib.import_module("api.search_api")
    state = {"owner": "user-a", "analysis_id": "a2f27ec4-7fd8-4871-b2b3-c8f2c6f8cbf8"}

    def fake_create(owner_subject: str) -> str:
        state["owner"] = owner_subject
        return state["analysis_id"]

    def fake_append(analysis_id, owner_subject, kind, filename, content_text, diagram_file_path=None):
        if analysis_id != state["analysis_id"] or owner_subject != state["owner"]:
            raise PermissionError("analysis_id does not belong to the caller")
        return None

    def fake_upsert(analysis_id, owner_subject, filename, file_path, erd_text):
        if analysis_id and analysis_id != state["analysis_id"]:
            raise PermissionError("analysis_id does not belong to the caller")
        state["owner"] = owner_subject
        return state["analysis_id"]

    def fake_update(analysis_id, owner_subject, diagram_filename, diagram_file_path, summary):
        if analysis_id != state["analysis_id"] or owner_subject != state["owner"]:
            raise PermissionError("analysis_id does not belong to the caller")
        return None

    class FakeQAService:
        def __init__(self, k=6):
            self.k = k

        def answer(self, q, **kwargs):
            if kwargs.get("owner_subject") != state["owner"]:
                raise PermissionError("analysis_id does not belong to the caller")
            return {"answer": f"ok:{q}", "sources": ["doc.pdf"]}

    monkeypatch.setattr(erd_module, "create_analysis_session", fake_create)
    monkeypatch.setattr(erd_module, "append_analysis_document", fake_append)
    monkeypatch.setattr(erd_module, "upsert_analysis_erd", fake_upsert)
    monkeypatch.setattr(erd_module, "update_analysis_diagram", fake_update)
    monkeypatch.setattr(erd_module, "_extract_text_from_saved_file", lambda p, n: ("hello", "txt"))
    monkeypatch.setattr(erd_module, "_vision_summary_from_bytes", lambda c, n, cfg: "diagram-summary")
    monkeypatch.setattr(search_module, "QAService", FakeQAService)

    client = _client()
    headers = _auth_header("user-a")

    create_res = client.post("/api/create-analysis-session", headers=headers)
    assert create_res.status_code == 200
    analysis_id = create_res.json()["analysis_id"]

    upload_text = client.post(
        "/api/append-text-document",
        headers=headers,
        files={"file": ("notes.txt", io.BytesIO(b"sample text"), "text/plain")},
        data={"filename": "notes.txt", "analysis_id": analysis_id, "doc_role": "supporting"},
    )
    assert upload_text.status_code == 200

    upload_diagram = client.post(
        "/api/append-architecture-diagram",
        headers=headers,
        files={"file": ("arch.png", io.BytesIO(b"\x89PNG\r\n\x1a\nabcdef"), "image/png")},
        data={"filename": "arch.png", "analysis_id": analysis_id},
    )
    assert upload_diagram.status_code == 200

    ask_ok = client.post(
        "/ask",
        headers=headers,
        json={"q": "threats?", "analysis_id": analysis_id, "structured": False, "k": 3},
    )
    assert ask_ok.status_code == 200
    assert "ok:threats?" in ask_ok.json()["answer"]

    ask_forbidden = client.post(
        "/ask",
        headers=_auth_header("user-b"),
        json={"q": "threats?", "analysis_id": analysis_id, "structured": False, "k": 3},
    )
    assert ask_forbidden.status_code in {403, 500}
