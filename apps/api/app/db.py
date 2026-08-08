from __future__ import annotations

import json
import os
import sqlite3
import threading

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "steuerhelfer.db")
DB_PATH = os.path.normpath(DB_PATH)

_local = threading.local()


def get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


def init_db() -> None:
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS tax_returns (
            tax_return_id TEXT PRIMARY KEY,
            tax_year INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            profile_json TEXT NOT NULL DEFAULT '{}',
            required_anlagen_json TEXT NOT NULL DEFAULT '[]',
            sections_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,
            file_name TEXT NOT NULL,
            content_type TEXT NOT NULL DEFAULT 'application/octet-stream',
            classification TEXT NOT NULL DEFAULT 'unknown',
            file_size INTEGER NOT NULL DEFAULT 0,
            extracted_fields_json TEXT NOT NULL DEFAULT '{}',
            confidence REAL NOT NULL DEFAULT 0.0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS expenses (
            expense_id TEXT PRIMARY KEY,
            tax_return_id TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            amount_eur REAL NOT NULL,
            date TEXT NOT NULL,
            receipt_document_id TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (tax_return_id) REFERENCES tax_returns(tax_return_id)
        );

        CREATE TABLE IF NOT EXISTS llm_configs (
            user_id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            api_key TEXT NOT NULL,
            model_name TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
    """)
    conn.commit()
