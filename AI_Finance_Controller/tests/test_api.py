import io

import pandas as pd


def _csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode()


def _sample_csv_bytes(n=10) -> bytes:
    df = pd.DataFrame({
        "payment_id": [f"p{i}" for i in range(n)],
        "payment_amount": [1000.0] * n,
        "fee": [20.0] * n,
        "tax": [5.0] * n,
        "refund": [0.0] * n,
        "adjustment": [0.0] * n,
        "actual_settlement": [975.0] * (n - 1) + [500.0],  # last row is an exception
    })
    return _csv_bytes(df)


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["auth_enabled"] is False


def test_demo_results(client):
    resp = client.get("/api/results")
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["total"] == 100
    assert body["source"] == "demo"


def test_upload_success(client):
    resp = client.post(
        "/api/upload",
        files={"file": ("payments.csv", _sample_csv_bytes(10), "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "DONE"
    assert body["summary"]["total"] == 10
    assert body["filename"] == "payments.csv"
    assert "uploadId" in body
    assert body["modelVersion"]  # a real (non-empty) model version string


def test_upload_then_refetch(client):
    resp = client.post(
        "/api/upload",
        files={"file": ("payments.csv", _sample_csv_bytes(5), "text/csv")},
    )
    upload_id = resp.json()["uploadId"]

    refetch = client.get(f"/api/upload/{upload_id}")
    assert refetch.status_code == 200
    assert refetch.json()["summary"]["total"] == 5


def test_upload_writes_audit_log(client):
    resp = client.post(
        "/api/upload",
        files={"file": ("payments.csv", _sample_csv_bytes(5), "text/csv")},
    )
    upload_id = resp.json()["uploadId"]

    audit = client.get(f"/api/audit/{upload_id}")
    assert audit.status_code == 200
    entries = audit.json()["entries"]
    assert len(entries) == 5
    assert entries[0]["actor"] == "anonymous"
    assert entries[0]["modelVersion"]


def test_upload_rejects_non_csv(client):
    resp = client.post(
        "/api/upload",
        files={"file": ("payments.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


def test_upload_rejects_empty_file(client):
    resp = client.post(
        "/api/upload",
        files={"file": ("payments.csv", b"", "text/csv")},
    )
    assert resp.status_code == 400


def test_upload_rejects_missing_columns(client):
    bad = pd.DataFrame({"foo": [1, 2], "bar": [3, 4]})
    resp = client.post(
        "/api/upload",
        files={"file": ("payments.csv", _csv_bytes(bad), "text/csv")},
    )
    assert resp.status_code == 422
    errors = resp.json()["detail"]["errors"]
    assert any("payment_id" in e for e in errors)


def test_upload_rejects_oversized_file(client, monkeypatch):
    import api_server

    monkeypatch.setattr(api_server, "MAX_UPLOAD_BYTES", 100)
    resp = client.post(
        "/api/upload",
        files={"file": ("payments.csv", _sample_csv_bytes(50), "text/csv")},
    )
    assert resp.status_code == 413


def test_nonexistent_upload_returns_404(client):
    resp = client.get("/api/upload/does-not-exist")
    assert resp.status_code == 404


# --- Auth ---


def test_upload_requires_key_when_auth_enabled(auth_client):
    resp = auth_client.post(
        "/api/upload",
        files={"file": ("payments.csv", _sample_csv_bytes(3), "text/csv")},
    )
    assert resp.status_code == 401


def test_upload_rejects_wrong_key(auth_client):
    resp = auth_client.post(
        "/api/upload",
        headers={"X-API-Key": "wrong-key"},
        files={"file": ("payments.csv", _sample_csv_bytes(3), "text/csv")},
    )
    assert resp.status_code == 401


def test_upload_succeeds_with_correct_key(auth_client):
    resp = auth_client.post(
        "/api/upload",
        headers={"X-API-Key": "test-key-123"},
        files={"file": ("payments.csv", _sample_csv_bytes(3), "text/csv")},
    )
    assert resp.status_code == 200
    audit = auth_client.get(f"/api/audit/{resp.json()['uploadId']}")
    assert audit.json()["entries"][0]["actor"] == "tester"


def test_upload_rate_limit_enforced(auth_client):
    # auth_client fixture sets RATE_LIMIT_UPLOADS_PER_HOUR=2
    headers = {"X-API-Key": "test-key-123"}
    for _ in range(2):
        resp = auth_client.post(
            "/api/upload",
            headers=headers,
            files={"file": ("payments.csv", _sample_csv_bytes(3), "text/csv")},
        )
        assert resp.status_code == 200

    third = auth_client.post(
        "/api/upload",
        headers=headers,
        files={"file": ("payments.csv", _sample_csv_bytes(3), "text/csv")},
    )
    assert third.status_code == 429
    assert "Retry-After" in third.headers
