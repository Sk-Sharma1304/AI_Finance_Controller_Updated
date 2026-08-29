# AI Finance Controller — Full Stack (Hackathon Build)

A multi-agent settlement reconciliation & fraud-control pipeline with a
**real trained IsolationForest anomaly model**, wired end-to-end to a
Next.js control-tower dashboard.

```
frontend-interface/   Next.js dashboard (control tower UI)
AI_Finance_Controller/  Python ML pipeline + FastAPI bridge (the "backend")
```

## What's actually running

- `AI_Finance_Controller/agents/anomaly_agent.py` trains a fresh
  **scikit-learn `IsolationForest(contamination=0.25)`** on every pipeline
  run — this is a real, live-trained ML model, not a canned result.
- `AI_Finance_Controller/api_server.py` is a small FastAPI app that runs
  the full 8-agent pipeline (reconciliation → duplicates → anomaly
  detection → risk scoring → investigation → LLM review → decision →
  action) and serves the result as JSON.
- The Next.js frontend (`frontend-interface/`) calls that API on page
  load. If the API isn't running, it falls back to a bundled
  TypeScript simulation of the same pipeline over static demo data, so
  the UI never breaks — but you want the real backend running for the
  "Live model" badge and real trained-model output.

## Quick start

You need Python 3.10+ and Node 18+.

### 1. Start the backend (Python / FastAPI)

```bash
cd AI_Finance_Controller
pip install -r requirements.txt
uvicorn api_server:app --reload --port 8000
```

Leave this running. Check it's healthy:

```bash
curl http://localhost:8000/api/health
```

Optional: set an OpenAI key to enable the real LLM investigation step
(otherwise the pipeline runs rule-based-only and still works fine):

```bash
export OPENAI_API_KEY="sk-..."
```

### 2. Start the frontend (Next.js)

In a second terminal:

```bash
cd frontend-interface
npm install
npm run dev
```

Open **http://localhost:3000**. You should see a **"Live model · Python
backend"** badge in the header — that means the dashboard is showing
real output from the trained IsolationForest, not the demo fallback.

### 3. (Optional) Run the CLI pipeline / evaluation directly

```bash
cd AI_Finance_Controller
python main.py                                  # full pipeline, writes outputs/*.csv
python evaluation/evaluate_anomaly_model.py      # model metrics
python evaluation/evaluate_reconciliation_model.py
streamlit run dashboard/app.py                   # optional Streamlit demo view
```

## What was fixed/changed for this build

- **Merged** the two separate projects: the FastAPI bridge
  (`api_server.py`) exposes the Python ML pipeline as JSON, and the
  frontend's data layer (`lib/pipeline/index.ts`) now fetches from it
  live, with a labeled fallback to the static demo data if the backend
  is offline.
- **Fixed a real bug** in `duplicates_detection_agent.py`: it was
  falling back to matching on `amount` alone (since this dataset has no
  `merchant_id`/`transaction_date`), which flagged 100% of transactions
  as duplicates. It now requires ≥2 identifying columns before trusting
  that path, so it correctly relies on the scenario-based check
  (5 genuine duplicates, matching ground truth).
- **Removed all Vercel branding**: `@vercel/analytics` dependency and
  usage, the `generator: 'v0.app'` metadata tag, and unused
  placeholder/logo image assets.
- **Verified the ML model**: ran the full pipeline and both evaluation
  scripts. IsolationForest/RandomForest on the engineered ratio
  features score 1.00 precision/recall/F1/ROC-AUC on this dataset; a
  raw-field IsolationForest scores far worse (0.75/0.36/0.49/0.68) —
  confirming the project's central finding that feature engineering,
  not model choice, is what makes detection work here.

## Notes for judges / demo

- The dataset is synthetic (100 transactions) — see the original
  `AI_Finance_Controller/readme.md` for full methodology, architecture
  rationale, and known limitations.
- No `OPENAI_API_KEY` is required to run this end-to-end; the LLM
  investigation agent gracefully no-ops and the rest of the pipeline
  (including the real ML anomaly model) still runs and is shown live.
