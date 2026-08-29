# AI Finance Controller — Production Readiness Roadmap

This document has two parts:

1. **What's done** — the core-engine fix plus the hardening pass that
   followed it (auth, persistence, audit logging, a trained/versioned
   model, tests, containerization, CI).
2. **What's still open** before this should touch real settlement
   money at real scale.

---

## 1. What's done

### 1.1 The core fix: works on any uploaded CSV, not just the demo dataset

The pipeline used to score every transaction by reading a `scenario`
column — a label like `"missing_settlement"` that only exists in the
bundled synthetic dataset because it's literally the answer key for
the injected test cases. A real payments export never has that
column, so the pipeline couldn't score anything it wasn't handed the
answer for.

- **`data_loader.py`** validates any uploaded CSV and computes
  `expected_settlement` directly from the raw fields:
  `payment_amount - fee - tax - refund + adjustment`. Verified
  numerically against all 100 rows / 8 scenario types of the demo
  dataset (100% match), enforces required columns, coerces numeric
  types, catches duplicate `payment_id`s, defaults optional columns
  to 0, and neutralizes CSV/spreadsheet formula injection.
- **`risk_agent.py`, `investigation_agent.py`, `decision_agent.py`,
  `action_agent.py`** score off signals every upload actually has —
  reconciliation status/severity, duplicate flags, the ML anomaly
  flag, financial impact — instead of the scenario label. Reproduces
  the same risk distribution as the original scenario-based scoring.

### 1.2 Trained, versioned ML model

- `ml/train_anomaly_model.py` trains the IsolationForest offline
  (not refit per request) and saves it with a version tag via
  `ml/registry.py` (`ml/models/anomaly_model_v<timestamp>.joblib` +
  metadata: features, contamination, training date, row count).
- `anomaly_agent.py` loads the latest registered model at inference
  time; every scored transaction carries `anomaly_model_version` so
  you always know which model produced a given decision.
- Retrain with `python ml/train_anomaly_model.py` when you have new
  historical data; it registers a new version without touching code.

### 1.3 Auth, rate limiting, persistence, audit logging

- **`auth.py`** — API-key auth via `X-API-Key` header, keys set
  through `API_KEYS=name:key,name2:key2`. Disabled by default for
  local dev (with a startup warning), so nothing breaks if you
  haven't set it up yet.
- **`rate_limit.py`** — per-actor upload quota
  (`RATE_LIMIT_UPLOADS_PER_HOUR`), in-memory token bucket, returns
  429 + `Retry-After` when exceeded.
- **`db.py`** — SQLite-backed persistence (via SQLAlchemy, so
  swapping to Postgres is a `DATABASE_URL` change, not a rewrite):
  `uploads` (results, status, row count) and `audit_log` (one row
  per transaction per run: decision, score, action, model version,
  actor, timestamp) tables. Survives restarts.
- **`GET /api/audit/{uploadId}`** — the append-only decision log,
  also viewable in the frontend's new audit-trail panel.
- **`logging_config.py`** — structured JSON logs for every request
  (method, path, status, duration) and every upload (rows, model
  version, actor).

### 1.4 Async processing for large files

Large uploads are handed to a background task; the client gets a
job id immediately and polls `GET /api/jobs/{uploadId}` (or the
upload panel does this automatically) instead of blocking the HTTP
request for the full pipeline duration.

### 1.5 Tests

33 pytest tests in `tests/`:
- `test_data_loader.py` — every validation path (missing columns,
  duplicate ids, non-numeric amounts, row limits, formula injection,
  the expected-settlement formula against the real ground-truth
  file).
- `test_pipeline_agents.py` — proves the rewritten agents score
  correctly with **zero** `scenario` column present (the regression
  guard for the core fix).
- `test_api.py` — full integration tests: upload success/error paths,
  auth (401 on missing/wrong key), rate limiting (429 after quota),
  audit log population.
- `test_regression_demo_dataset.py` — pins the trained model's
  decision distribution on the demo dataset so an accidental
  retraining/reweighting regression is caught in CI.

Run with `python -m pytest tests/ -v` from `AI_Finance_Controller/`.

### 1.6 Containerization & CI

- `AI_Finance_Controller/Dockerfile` — non-root user, healthcheck,
  bakes in the trained model so the image serves real predictions
  on first boot.
- `frontend-interface/Dockerfile` — multi-stage build using Next.js
  `output: "standalone"`.
- `docker-compose.yml` (repo root) — runs both together locally with
  a persistent volume for the SQLite file.
- `.github/workflows/ci.yml` — backend test job, frontend
  typecheck+build job, then a Docker image build job gated on both.

> **Not verified by execution:** no Docker daemon was available in
> the environment this was built in, so the Dockerfiles/compose file
> are syntax-checked and logically standard but not build-tested.
> Run `docker compose up --build` yourself before trusting them in a
> real deploy.

### 1.7 Frontend

- Drag-and-drop upload panel: API-key field (persisted locally, sent
  as `X-API-Key`), clear 401/429/422 error messages, automatic job
  polling for async (large-file) uploads.
- Audit-trail viewer showing the per-transaction decision log.
- Model version surfaced in the dashboard footer.
- **Fixed a real crash**: the UI originally assumed every transaction
  has a `scenario` field (a demo-dataset-only column). Any real
  upload — which never has it — crashed `scenarioLabel()`. Fixed by
  making `scenario`/`status`/`order_id` optional throughout the type
  system and adding a `transactionTag()` fallback that derives a
  label (Reconciled / Discrepancy / Missing Settlement / Duplicate)
  from the actual computed signals when scenario is absent. Verified
  against a real uploaded file with zero crashes.

---

## 2. What's still open

### 2.1 Must-fix before any real money is touched

| Gap | Why it matters | Direction |
|---|---|---|
| **Auth is API-key only, and off by default** | API keys are simple but weak (no expiry, no scoping, no rotation built in, shared secret in an env var). | Move to OAuth/OIDC or signed short-lived tokens for anything beyond internal/demo use; keep API keys only for service-to-service calls. |
| **No action *execution*, only recommendation** | The system recommends `HOLD_SETTLEMENT` etc. but has no integration to actually place a hold — likely intentional (human-in-the-loop), but should be explicit in the product. | Decide and document: always advisory, or does a future version call a payments/ledger API? If advisory, say so in the UI so nobody assumes an action was taken automatically. |
| **SQLite, not Postgres** | Fine for one process; doesn't work across multiple replicas, and SQLite under concurrent writes from several API instances will contend/lock. | `DATABASE_URL` already routes through SQLAlchemy — point it at a managed Postgres (RDS/Cloud SQL) instead of `sqlite:///...` for anything with more than one replica. |
| **Raw uploaded files aren't retained** | Only the *scored results* are persisted; the original CSV bytes aren't kept, which is a problem for audit/dispute resolution ("what exactly did the merchant submit"). | Store the raw upload in object storage (S3/GCS) alongside the DB row, keyed by `uploadId`. |

### 2.2 Should-fix before general production use

| Gap | Why it matters | Direction |
|---|---|---|
| **Async job queue is in-process (`BackgroundTasks`), not a real queue** | Works for one server instance; if the process restarts mid-job, the job is lost — no retry, no visibility across replicas. | Move to Celery/RQ/Cloud Tasks with Redis or SQS as the broker once you run more than one API replica. |
| **Rate limiter is in-memory, per-process** | Multiple replicas each track their own quota — someone can get `N × replica_count` uploads/hour instead of `N`. | Move to Redis-backed rate limiting (e.g. `redis` + a sliding-window or token-bucket library) so quota is shared across replicas. |
| **No malware/antivirus scanning on uploads** | A `.csv` extension doesn't guarantee CSV content; CSV-injection is now sanitized, but a genuinely malicious file (e.g. disguised binary) isn't scanned. | Add ClamAV (or a cloud equivalent) in front of the upload path. |
| **LLM cost control is per-run, not per-user/day** | `MAX_LLM_CALLS` caps calls within a single pipeline run, but there's no daily budget per API key or global spend alarm. | Add per-key daily/monthly LLM call quotas and a spend alert; the pipeline already degrades gracefully to rule-based-only scoring if the LLM is skipped. |
| **No metrics/tracing beyond logs** | Structured JSON logs exist, but there's no dashboard for latency percentiles, error rate, or LLM spend over time. | Add OpenTelemetry instrumentation → your APM of choice (Datadog/Honeycomb/Grafana). |
| **CI builds Docker images but doesn't push/deploy them** | `docker-build` job in CI proves the images build; nothing ships anywhere yet. | Add a registry push (ECR/GHCR) gated on `main`, then a deploy step for your platform (ECS/Cloud Run/k8s). |

### 2.3 Model quality / correctness

| Gap | Why it matters | Direction |
|---|---|---|
| **Risk weights are hand-tuned, not learned** | The signal-based scoring formula was designed to match the *shape* of the old scenario-based scores, not derived from real outcome data. | Once you have real labeled outcomes (which flagged transactions were actually fraud/error vs. false positives), fit the weights properly — even a simple logistic regression over the same features beats hand-tuned weights and gives calibrated probabilities. |
| **IsolationForest trained on 100 synthetic rows** | `ml/models/` currently ships a model trained on the bundled demo dataset — fine for demoing the *mechanism* (train-once, version, load-at-inference), not for real anomaly detection. | Retrain (`python ml/train_anomaly_model.py`) against real historical transaction data before relying on the anomaly signal in production. |
| **Duplicate detection depends on optional columns** | Reliable duplicate detection needs `merchant_id` + `amount` (+ ideally `transaction_date`); a minimal upload with just the 3 required columns gets zero duplicate detection, silently. | Surface this in the API response — tell the user which optional columns were missing and what signal was skipped, rather than silently returning `duplicate_flag: false` for everything. |
| **No structured feature attribution** | `investigation_summary` is a decent human-readable explanation, but there's no per-decision feature-importance output for compliance review. | If this needs to satisfy a compliance reviewer, add SHAP-style attribution once the model moves off hand-tuned weights. |

### 2.4 Scale / cost

| Gap | Why it matters | Direction |
|---|---|---|
| **50,000-row synchronous cutoff, no true chunking above it** | `data_loader.MAX_ROWS` rejects larger files outright rather than processing them in batches. | Extend the async job path to chunk very large files and stream/paginate results back instead of one large JSON payload. |
| **In-memory rate-limit and job state don't survive a restart** | A deploy/restart silently resets everyone's quota and drops in-flight background jobs. | Covered by the Redis + real queue moves above (2.2) — do those together. |

---

## Suggested sequencing

1. Point `DATABASE_URL` at Postgres and add object storage for raw
   uploads (2.1) — the SQLite path is dev-only past a single replica.
2. Move auth to OAuth/OIDC if this is customer-facing (2.1).
3. Retrain the model on real data once you have it (2.3) — the
   train/version/load mechanism is already built.
4. Redis for rate limiting + a real job queue once you run more than
   one API replica (2.2).
5. Metrics/tracing + CI image push & deploy (2.2).
6. Everything else, as real usage surfaces what actually matters.
