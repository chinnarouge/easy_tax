from fastapi.testclient import TestClient

from apps.api.app.main import app

client = TestClient(app)


def _get_token() -> str:
    import time
    email = f"llm-test-{time.time()}@example.com"
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "test123", "full_name": "LLM Tester"},
    )
    return res.json()["token"]


def test_list_providers() -> None:
    response = client.get("/api/v1/llm/providers")
    assert response.status_code == 200
    providers = response.json()["providers"]
    assert "openai" in providers
    assert "anthropic" in providers
    assert "google" in providers
    assert "mistral" in providers
    assert "cohere" in providers
    assert "custom" in providers


def test_save_and_get_llm_settings() -> None:
    token = _get_token()
    headers = {"Authorization": f"Bearer {token}"}

    save = client.post(
        "/api/v1/llm/settings",
        json={"provider": "openai", "api_key": "sk-test-abc123xyz789", "model_name": "gpt-4o"},
        headers=headers,
    )
    assert save.status_code == 200
    body = save.json()
    assert body["provider"] == "openai"
    assert body["model_name"] == "gpt-4o"
    assert body["active"] is True
    assert "sk-t" in body["key_preview"]
    assert "z789" in body["key_preview"]

    get = client.get("/api/v1/llm/settings", headers=headers)
    assert get.status_code == 200
    assert get.json()["configured"] is True
    assert get.json()["provider"] == "openai"


def test_save_with_default_model() -> None:
    token = _get_token()
    headers = {"Authorization": f"Bearer {token}"}

    save = client.post(
        "/api/v1/llm/settings",
        json={"provider": "anthropic", "api_key": "sk-ant-test123456789"},
        headers=headers,
    )
    assert save.status_code == 200
    assert save.json()["model_name"] == "claude-sonnet-5"


def test_delete_llm_settings() -> None:
    token = _get_token()
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/api/v1/llm/settings",
        json={"provider": "google", "api_key": "AIzaSy-test-key-12345"},
        headers=headers,
    )

    delete = client.delete("/api/v1/llm/settings", headers=headers)
    assert delete.status_code == 200
    assert delete.json()["deleted"] is True

    get = client.get("/api/v1/llm/settings", headers=headers)
    assert get.json()["configured"] is False


def test_llm_settings_requires_auth() -> None:
    response = client.post(
        "/api/v1/llm/settings",
        json={"provider": "openai", "api_key": "sk-test"},
    )
    assert response.status_code == 401
