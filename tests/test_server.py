import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from solar_finance_agent.server import app


def test_whatsapp_webhook_returns_missing_fields(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "/tmp/dummy.json")

    client = TestClient(app)
    resp = client.post("/webhooks/whatsapp", data={"Body": "project_name=Demo"})

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "needs_input"
    assert payload["channel"] == "whatsapp"
    assert "project_size_mw" in payload["missing_assumptions"]


def test_sms_webhook_missing_credentials(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)

    client = TestClient(app)
    resp = client.post("/webhooks/sms", data={"Body": "project_name=Demo"})

    assert resp.status_code == 500
    payload = resp.json()
    assert payload["status"] == "error"
