from __future__ import annotations

from dataclasses import dataclass

from apps.api.app.db import get_conn

SUPPORTED_PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        "default_model": "gpt-4o-mini",
    },
    "anthropic": {
        "name": "Anthropic",
        "models": ["claude-sonnet-5", "claude-haiku-4-5-20251001", "claude-opus-4-8"],
        "default_model": "claude-sonnet-5",
    },
    "google": {
        "name": "Google Gemini",
        "models": ["gemini-2.0-flash", "gemini-2.5-pro", "gemini-2.5-flash"],
        "default_model": "gemini-2.0-flash",
    },
    "mistral": {
        "name": "Mistral AI",
        "models": ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest"],
        "default_model": "mistral-large-latest",
    },
    "cohere": {
        "name": "Cohere",
        "models": ["command-r-plus", "command-r", "command-light"],
        "default_model": "command-r-plus",
    },
    "custom": {
        "name": "Custom / Self-hosted",
        "models": [],
        "default_model": "",
    },
}


@dataclass
class LlmConfig:
    provider: str
    api_key: str
    model_name: str
    active: bool = True


def save_llm_config(user_id: str, provider: str, api_key: str, model_name: str) -> LlmConfig:
    conn = get_conn()
    if not model_name and provider in SUPPORTED_PROVIDERS:
        model_name = SUPPORTED_PROVIDERS[provider]["default_model"]
    conn.execute(
        "INSERT INTO llm_configs (user_id, provider, api_key, model_name, active) VALUES (?, ?, ?, ?, 1) "
        "ON CONFLICT(user_id) DO UPDATE SET provider=excluded.provider, api_key=excluded.api_key, model_name=excluded.model_name, active=1",
        (user_id, provider, api_key, model_name),
    )
    conn.commit()
    return LlmConfig(provider=provider, api_key=api_key, model_name=model_name)


def get_llm_config(user_id: str) -> LlmConfig | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM llm_configs WHERE user_id = ?", (user_id,)).fetchone()
    if row is None:
        return None
    return LlmConfig(
        provider=row["provider"],
        api_key=row["api_key"],
        model_name=row["model_name"],
        active=bool(row["active"]),
    )


def delete_llm_config(user_id: str) -> bool:
    conn = get_conn()
    cursor = conn.execute("DELETE FROM llm_configs WHERE user_id = ?", (user_id,))
    conn.commit()
    return cursor.rowcount > 0
