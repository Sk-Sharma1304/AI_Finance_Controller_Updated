"""
Shared pytest fixtures.

The API client fixture is the important one: it reloads ``db`` and
``api_server`` with a fresh, isolated SQLite file per test (and
optional env overrides for auth/rate-limit tests) so tests don't
share state or leak into your real ``finance_controller.db``.
"""

from __future__ import annotations

import importlib
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def demo_dataframe():
    """The bundled 100-row synthetic dataset, validated (as any
    upload would be), WITHOUT the scenario/ground-truth columns --
    this is the realistic "what a user actually uploads" shape."""
    from data_loader import prepare_dataframe

    raw = pd.read_csv(
        os.path.join(os.path.dirname(__file__), "..", "data", "finance_controller_dataset.csv")
    )
    columns = [
        "payment_id", "order_id", "payment_amount", "fee", "tax",
        "refund", "adjustment", "actual_settlement",
    ]
    columns = [c for c in columns if c in raw.columns]
    return prepare_dataframe(raw[columns])


@pytest.fixture
def minimal_valid_df():
    """The smallest possible valid upload: just the 3 required columns."""
    from data_loader import prepare_dataframe

    return prepare_dataframe(pd.DataFrame({
        "payment_id": ["p1", "p2", "p3"],
        "payment_amount": [1000.0, 500.0, 2000.0],
        "actual_settlement": [980.0, 500.0, 1500.0],
    }))


def make_client(tmp_path, monkeypatch, env: dict[str, str] | None = None):
    """Builds a TestClient backed by a throwaway SQLite file, with
    optional environment variables (API_KEYS, RATE_LIMIT_*) applied
    before the app module is (re)imported."""

    db_path = tmp_path / "test_finance_controller.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.delenv("API_KEYS", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    for key, value in (env or {}).items():
        monkeypatch.setenv(key, value)

    for mod_name in ["db", "auth", "rate_limit", "api_server"]:
        if mod_name in sys.modules:
            importlib.reload(sys.modules[mod_name])
        else:
            importlib.import_module(mod_name)

    import api_server as api_server_module
    from fastapi.testclient import TestClient

    return TestClient(api_server_module.app)


@pytest.fixture
def client(tmp_path, monkeypatch):
    return make_client(tmp_path, monkeypatch)


@pytest.fixture
def auth_client(tmp_path, monkeypatch):
    return make_client(
        tmp_path, monkeypatch,
        env={"API_KEYS": "tester:test-key-123", "RATE_LIMIT_UPLOADS_PER_HOUR": "2"},
    )
