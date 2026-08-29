"""
Authentication
=================

Simple API-key auth: every request to a protected endpoint must
send a valid key in the ``X-API-Key`` header. Keys are configured
via the ``API_KEYS`` environment variable as a comma-separated list
of ``name:key`` pairs, e.g.:

    API_KEYS="ops-dashboard:sk_live_abc123,ci-pipeline:sk_live_def456"

This is intentionally the simplest thing that could work, not a
full auth system. For a real production deployment, prefer:
  - OAuth2 / OIDC (e.g. via Auth0, Okta, or your identity provider)
    if there are human users logging in through the frontend.
  - Signed service-to-service tokens (mTLS or short-lived JWTs) for
    machine-to-machine calls (CI, batch jobs).

The key's "name" is threaded through as the ``actor`` on audit log
rows and upload records, so even this simple scheme gives you
"who scored this file" in the audit trail -- which is the part
that actually matters for compliance, more than the auth mechanism
itself.

If ``API_KEYS`` is unset, auth is disabled entirely and every
request is treated as actor "anonymous" -- this is what makes local
dev / the bundled demo work without extra setup, but it must NOT be
how this runs in production. ``api_server.py`` logs a warning on
startup if auth is disabled.
"""

from __future__ import annotations

import os

from fastapi import Header, HTTPException


def _load_keys() -> dict[str, str]:
    raw = os.environ.get("API_KEYS", "")
    keys: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        name, _, key = pair.partition(":")
        keys[key.strip()] = name.strip()
    return keys


_API_KEYS = _load_keys()


def auth_enabled() -> bool:
    return bool(_API_KEYS)


async def get_actor(x_api_key: str | None = Header(default=None)) -> str:
    """FastAPI dependency. Returns the actor name for audit logging.
    Raises 401 if auth is enabled and the key is missing/invalid."""

    if not _API_KEYS:
        return "anonymous"  # auth disabled -- see module docstring

    if not x_api_key or x_api_key not in _API_KEYS:
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid API key. Send it in the X-API-Key header.",
        )

    return _API_KEYS[x_api_key]
