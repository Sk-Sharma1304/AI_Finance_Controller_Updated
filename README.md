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

# AI Finance Controller

> An AI-powered financial control system that automatically reconciles transactions, detects duplicates and anomalies, assesses financial risk, investigates exceptions, and escalates only the cases that require human judgment.

[![CI](https://github.com/Sk-Sharma1304/AI_Finance_Controller_Updated/actions/workflows/ci.yml/badge.svg)](https://github.com/Sk-Sharma1304/AI_Finance_Controller_Updated/actions/workflows/ci.yml)

---

## 🚀 Overview

**AI Finance Controller** is a full-stack, multi-agent financial operations system designed to automate the first level of payment reconciliation and exception handling.

Instead of relying on a single rule or a single AI model, the system combines:

- Deterministic financial reconciliation
- Duplicate transaction detection
- Machine-learning anomaly detection
- Risk scoring
- Rule-based investigation
- LLM-assisted investigation
- Final decision intelligence
- Recommended operational actions
- Audit logging
- Human-in-the-loop escalation

The system is designed around one core question:

> **Can an AI financial controller reliably decide which transactions are normal, which require investigation, and which require human intervention — while explaining why?**

---

# 🎯 Problem Statement

Payment and settlement systems generate thousands or millions of financial transactions.

A typical reconciliation process involves comparing:

```text
Payment Amount
        ↓
Fees / Taxes / Refunds / Adjustments
        ↓
Expected Settlement
        ↓
Actual Settlement
```
# Solution

AI Finance Controller processes every transaction through a sequence of specialized agents.

```text 

                    Transaction Data
                           │
                           ▼
                ┌─────────────────────┐
                │ Data Validation &   │
                │ Normalization       │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Reconciliation      │
                │ Agent               │
                └──────────┬──────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
   ┌───────────────────┐       ┌───────────────────┐
   │ Duplicate         │       │ ML Anomaly        │
   │ Detection Agent   │       │ Detection Agent   │
   └─────────┬─────────┘       └─────────┬─────────┘
             └─────────────┬─────────────┘
                           ▼
                ┌─────────────────────┐
                │ Risk Assessment     │
                │ Agent               │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Investigation       │
                │ Agent               │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ LLM Investigation   │
                │ Agent (Optional)    │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Decision Agent      │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Action Agent        │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Control Tower       │
                │ Dashboard           │
                └─────────────────────┘
```
🤖 Multi-Agent Architecture

The system uses specialized agents instead of putting all financial logic into one model.

1. Reconciliation Agent

Performs deterministic financial reconciliation.

The expected settlement is calculated as:

Expected Settlement =
Payment Amount
- Fee
- Tax
- Refund
+ Adjustment

It then compares:

Expected Settlement
        vs
Actual Settlement

and generates reconciliation signals such as:

Settlement deviation
Deviation ratio
Reconciliation status
Severity
Financial impact

2. Duplicate Detection Agent

Identifies transactions that may represent the same financial event more than once.

The system avoids relying on a single weak signal such as amount alone.

Where sufficient identifying fields exist, it considers transaction attributes such as:

Payment ID
Merchant ID
Transaction date
Amount
Other identifying information

This reduces false duplicate classifications.

3. ML Anomaly Detection Agent

The system uses a trained scikit-learn Isolation Forest to detect statistically unusual transactions.

The model operates on engineered financial features rather than simply looking at raw transaction values.

Examples of engineered signals include:

fee_ratio
tax_ratio
refund_ratio
adjustment_ratio
settlement_ratio
settlement_deviation_ratio
absolute_deviation_ratio
Why Isolation Forest?

Isolation Forest is suitable for this problem because many financial anomalies are rare and labeled examples may be limited.

It allows the system to identify unusual behavior without requiring every possible fraud pattern to be manually labeled.

The model is:

Trained offline
Versioned
Persisted
Loaded during inference
Attached to every scored transaction through anomaly_model_version
4. Risk Assessment Agent

Converts financial evidence into a risk score.

The agent considers signals such as:

Reconciliation severity
Financial impact
Duplicate detection
ML anomaly signal
Exception evidence

The result includes:

Risk Score: 0 – 100

Risk Level:
LOW
MEDIUM
HIGH
CRITICAL
5. Investigation Agent

The rule-based investigation agent combines the available evidence and produces:

Investigation summary
Reason for the exception
Supporting signals
Recommended action

This provides deterministic reasoning before involving an LLM.

🧠 6. LLM Investigation Agent

The LLM is not used simply to generate a nicer explanation.

It acts as an independent second opinion.

The LLM receives the transaction evidence and returns structured information such as:

{
  "narrative": "...",
  "risk_opinion": "HIGH",
  "confidence": 0.87,
  "recommended_action": "MANUAL_REVIEW"
}

The Decision Agent can use this independent opinion.

For example:

Rule-based system → NORMAL

LLM opinion → HIGH
LLM confidence → ≥ 0.7

                    ↓

           AI_ESCALATED_REVIEW

This creates a human-in-the-loop safety mechanism rather than allowing the LLM to directly execute financial actions.

💰 Cost-Aware AI Design

The LLM is intentionally not called for every transaction.

The pipeline first uses deterministic rules and ML signals.

Only transactions that are potentially important are considered for LLM investigation.

Examples:

Higher risk transactions
Duplicate transactions
ML anomalies
Transactions requiring deeper investigation

There is also a configurable LLM call limit.

MAX_LLM_CALLS=25

This reduces:

API cost
Latency
Unnecessary LLM usage

If no OpenAI API key is provided, the system automatically falls back to the rule-based pipeline.

Therefore:

LLM available
      ↓
Rules + ML + LLM investigation

LLM unavailable
      ↓
Rules + ML investigation

The system continues to operate in both cases.

⚖️ 7. Decision Agent

The Decision Agent combines the outputs of the previous stages.

It considers:

Reconciliation result
Duplicate flag
ML anomaly
Risk score
Rule-based investigation
LLM investigation

Possible decisions include:

NORMAL
FINANCIAL_EXCEPTION
CONFIRMED_HIGH_PRIORITY
AI_ESCALATED_REVIEW

The objective is not to maximize the number of flagged transactions.

The objective is to identify:

Which transactions genuinely require attention?

⚡ 8. Action Agent

The final agent converts a decision into an operational recommendation.

Examples include:

NO_ACTION
MANUAL_REVIEW
HOLD_SETTLEMENT
BLOCK_DUPLICATE
AI_FLAGGED_MANUAL_REVIEW

Each action is accompanied by:

Priority
Reason
Financial impact
Supporting evidence
Important

The current system is advisory.

It recommends actions but does not directly execute settlement holds, refunds, or payment blocking against a real payment gateway.

This preserves the human-in-the-loop design.

🖥️ Control Tower Dashboard

The frontend provides a financial operations control tower.

It provides visibility into:

Total transactions
Auto-cleared transactions
Flagged transactions
AI escalations
Financial impact
Risk distribution
Transaction details
Priority queue
Agent trail
Audit trail
Model version
Upload status

The dashboard connects directly to the FastAPI backend.

Next.js Frontend
       │
       │ HTTP / JSON
       ▼
FastAPI Backend
       │
       ▼
Multi-Agent Pipeline
       │
       ├── Reconciliation
       ├── Duplicate Detection
       ├── ML Anomaly Detection
       ├── Risk Assessment
       ├── Investigation
       ├── LLM Investigation
       ├── Decision
       └── Action
📂 Project Structure
AI_Finance_Controller_FULLSTACK/
│
├── AI_Finance_Controller/
│   │
│   ├── agents/
│   │   ├── reconciliation_agent.py
│   │   ├── duplicates_detection_agent.py
│   │   ├── anomaly_agent.py
│   │   ├── risk_agent.py
│   │   ├── investigation_agent.py
│   │   ├── llm_investigation_agent.py
│   │   ├── decision_agent.py
│   │   └── action_agent.py
│   │
│   ├── orchestrator/
│   │   └── finance_orchestrator.py
│   │
│   ├── ml/
│   │   ├── train_anomaly_model.py
│   │   ├── registry.py
│   │   └── models/
│   │       ├── latest.json
│   │       └── anomaly_model_*.joblib
│   │
│   ├── evaluation/
│   │   ├── labels.py
│   │   ├── evaluate_anomaly_model.py
│   │   └── evaluate_reconciliation_model.py
│   │
│   ├── tests/
│   │   ├── test_api.py
│   │   ├── test_data_loader.py
│   │   ├── test_pipeline_agents.py
│   │   └── test_regression_demo_dataset.py
│   │
│   ├── dashboard/
│   │   └── app.py
│   │
│   ├── data/
│   │   ├── finance_controller_dataset.csv
│   │   ├── ground_truth.csv
│   │   ├── finance_features.csv
│   │   └── reconciliation_features.csv
│   │
│   ├── api_server.py
│   ├── data_loader.py
│   ├── auth.py
│   ├── rate_limit.py
│   ├── db.py
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend-interface/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── package.json
│   ├── Dockerfile
│   └── next.config.mjs
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── docker-compose.yml
├── PRODUCTION_ROADMAP.md
└── README.md
🛠️ Tech Stack
Backend
Python
FastAPI
Pandas
Scikit-learn
SQLAlchemy
SQLite
Pytest
Machine Learning
Isolation Forest
Feature engineering
Model versioning
Offline model training
AI
OpenAI API
Structured JSON LLM responses
Rule-based + LLM hybrid investigation
Frontend
Next.js
React
TypeScript
Tailwind CSS
Recharts
DevOps
Docker
Docker Compose
GitHub Actions
CI testing
📥 Input Data

The system accepts a payments CSV.

Required columns
payment_id
payment_amount
actual_settlement
Optional columns
fee
tax
refund
adjustment
merchant_id
transaction_date

If optional financial columns are not present, they default to 0.

The system automatically calculates:

expected_settlement =
payment_amount
- fee
- tax
- refund
+ adjustment

A real uploaded CSV does not require a scenario or ground_truth column.

This is important because real payment exports do not contain the answer to the problem they are being evaluated on.

🚀 Getting Started
Prerequisites

Make sure you have:

Python 3.10+
Node.js 18+
npm
Git

Docker is optional.

Option 1 — Run Locally
Step 1 — Clone the repository
git clone https://github.com/Sk-Sharma1304/AI_Finance_Controller_Updated.git
cd AI_Finance_Controller_Updated
Step 2 — Start the Python Backend

Open Terminal 1:

cd AI_Finance_Controller

Create a virtual environment:

Windows
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

Install dependencies:

pip install -r requirements.txt

Start FastAPI:

uvicorn api_server:app --reload --port 8000

Backend:

http://localhost:8000

Health check:

http://localhost:8000/api/health
Step 3 — Start the Frontend

Open Terminal 2:

cd frontend-interface
npm install
npm run dev

Open:

http://localhost:3000

The dashboard should connect to:

http://localhost:8000

When the backend is available, the dashboard displays the live backend/model status.

🔑 Optional OpenAI Configuration

The LLM investigation layer is optional.

Windows PowerShell
$env:OPENAI_API_KEY="your_api_key"
Linux / macOS
export OPENAI_API_KEY="your_api_key"

Optional model:

export OPENAI_MODEL="gpt-4o-mini"

Optional per-run call limit:

export MAX_LLM_CALLS="25"

The project still works without an OpenAI key.

🐳 Run with Docker

The repository includes Dockerfiles for both services and a Docker Compose configuration.

From the repository root:

docker compose up --build

Then open:

Frontend:
http://localhost:3000

Backend:
http://localhost:8000

Health:
http://localhost:8000/api/health

Docker Compose runs:

Frontend container
        │
        ▼
Next.js

Backend container
        │
        ▼
FastAPI
        │
        ▼
AI Finance Controller

The default Compose setup uses SQLite with a persistent Docker volume for local/demo use.

🧪 Running Tests

From:

AI_Finance_Controller/

run:

python -m pytest tests/ -v

The test suite covers:

Data validation
Required columns
Numeric validation
Duplicate payment IDs
Formula injection protection
Expected settlement calculation
Agent pipeline behavior
API upload flow
Authentication
Rate limiting
Audit logging
Regression behavior
📊 Model Evaluation

The project includes dedicated evaluation scripts.

Run:

python evaluation/evaluate_anomaly_model.py

and:

python evaluation/evaluate_reconciliation_model.py

The ML model uses engineered financial ratios rather than relying only on raw transaction fields.

This was an important finding during development:

Feature engineering had a larger impact on anomaly detection quality than simply changing the model.

🔄 Train a New Anomaly Model

The trained model is stored and versioned under:

AI_Finance_Controller/ml/models/

To retrain:

python ml/train_anomaly_model.py

The model registry creates a new version rather than overwriting the previous model.

Each pipeline result records the model version used for scoring.

This improves reproducibility and auditability.

🌐 API Endpoints

The FastAPI backend exposes endpoints including:

Method	Endpoint	Purpose
GET	/api/health	Backend health/status
GET	/api/results	Run/get bundled demo results
POST	/api/rerun	Re-run demo pipeline
POST	/api/upload	Upload and score a CSV
GET	/api/jobs/{upload_id}	Check async upload status
GET	/api/upload/{upload_id}	Retrieve uploaded results
GET	/api/audit/{upload_id}	Retrieve audit trail
🔐 Security & Reliability Features

The project includes several safeguards beyond the basic ML pipeline.

API Authentication

API-key authentication is supported using:

X-API-Key

Configure keys through:

API_KEYS=name:key,name2:key

Authentication is disabled by default for local development.

Rate Limiting

Upload requests can be rate-limited per actor.

Default:

30 uploads/hour

The LLM investigation layer also has a daily row budget to help control API spending.

Data Validation

Uploaded CSV files are validated before scoring.

The system checks:

Required columns
Empty files
Maximum row count
Duplicate payment IDs
Numeric fields
Positive payment amounts
Safe handling of spreadsheet formulas
Audit Trail

Every scored transaction can be associated with:

Upload ID
Payment ID
Risk score
Risk level
Final decision
Recommended action
Financial impact
Model version
Actor
Timestamp

This creates an auditable record of how the financial decision was produced.

🧑‍⚖️ Human-in-the-Loop Design

The system intentionally does not attempt to automate every financial decision.

Instead:

                    Transaction
                         │
                         ▼
                 Automated Analysis
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
         NORMAL                  UNCERTAIN /
            │                    HIGH RISK
            ▼                         │
       Auto Clear                    ▼
                              Human Review

The objective is to reduce unnecessary manual work while preserving human oversight for high-impact or ambiguous cases.

📈 Demo Dataset

The repository contains a synthetic dataset of 100 transactions.

The dataset includes several scenarios such as:

Normal transactions
Refunds
Adjustments
Amount discrepancies
Missing settlements
Duplicate transactions
Wrong settlements
Unexplained differences

The ground_truth.csv file is used for evaluation of the bundled demo dataset.

It is not required for scoring user-uploaded data.

🧠 Important Engineering Decision

A major architectural improvement in this version is that the pipeline no longer depends on a hidden answer key.

Earlier versions relied on the scenario field from the synthetic dataset.

That would not work with real payment exports because:

Real transaction CSV
        ↓
Does NOT contain:
"this transaction is fraudulent"
"this transaction is duplicated"
"this transaction has a discrepancy"

The current system instead derives decisions from observable signals:

Raw Payment Data
      ↓
Expected Settlement
      ↓
Reconciliation Signals
      ↓
Duplicate Detection
      ↓
ML Anomaly Detection
      ↓
Risk Assessment
      ↓
Investigation
      ↓
Decision

This makes the architecture applicable to arbitrary compatible payment CSVs.

🏆 Key Differentiators
1. Multi-agent financial reasoning

Instead of one generic AI model:

Specialized financial agents
          ↓
Evidence aggregation
          ↓
Final decision
2. Hybrid AI

The system combines:

Deterministic Rules
        +
Machine Learning
        +
LLM Reasoning

Each component has a different responsibility.

3. LLM as an independent second opinion

The LLM can disagree with the deterministic pipeline.

This disagreement can trigger:

AI_ESCALATED_REVIEW

rather than blindly accepting the first decision.

4. Cost-aware AI

The LLM is only used when additional reasoning is potentially valuable.

This reduces unnecessary API calls and cost.

5. Explainability

Every decision is supported by:

Financial evidence
Risk score
Investigation result
Recommended action
Model version
Audit trail
6. Human-in-the-loop

The system does not pretend that every financial decision should be automated.

High-risk or ambiguous cases are surfaced for human review.

⚠️ Current Limitations

This project is a hackathon/prototype system and is not production-ready for directly controlling real settlement money.

Important limitations include:

Authentication

API-key authentication is currently supported.

A production deployment should use stronger identity and authorization mechanisms such as OAuth/OIDC or short-lived signed tokens.

Database

SQLite is suitable for local development and small deployments.

A production deployment should use PostgreSQL or another managed relational database.

Job Processing

Large-file processing currently uses in-process background tasks.

A production-scale system should use a durable queue such as:

Celery
Redis
SQS
Cloud Tasks
Rate Limiting

The current rate limiter is in-memory and therefore process-local.

A distributed deployment should use Redis or another shared store.

File Storage

The current system persists scored results and audit records.

A production implementation should also retain the original uploaded file in object storage such as:

Amazon S3
Google Cloud Storage
Azure Blob Storage
Action Execution

The Action Agent currently produces recommendations.

It does not directly execute:

Settlement holds
Refunds
Payment blocking
Ledger changes

This is intentional for the current human-in-the-loop design.

See:

PRODUCTION_ROADMAP.md

for the complete production-readiness roadmap.

🔮 Future Roadmap

Potential future improvements include:

PostgreSQL production database
Redis-based distributed rate limiting
Durable job queues
Object storage for raw uploads
OAuth/OIDC authentication
Real-time transaction streaming
Merchant-level behavioral profiling
Continuous model monitoring
Model drift detection
Human feedback loop
Active learning
Payment gateway integration
Automated settlement holds with approval workflows
Role-based access control
Real-time alerts
Multi-tenant architecture
🎥 Demo Flow

A typical demo follows this flow:

1. Open Control Tower
        ↓
2. Backend health is verified
        ↓
3. Load transaction data
        ↓
4. Reconciliation runs
        ↓
5. Duplicate detection runs
        ↓
6. ML anomaly detection runs
        ↓
7. Risk is calculated
        ↓
8. Transactions are investigated
        ↓
9. Selected cases receive LLM investigation
        ↓
10. Final decisions are generated
        ↓
11. Recommended actions are produced
        ↓
12. High-priority cases enter the review queue
        ↓
13. Audit trail records the decision
👨‍💻 Development

Backend:

cd AI_Finance_Controller
python main.py

Frontend:

cd frontend-interface
npm run dev

Tests:

cd AI_Finance_Controller
python -m pytest tests/ -v
📜 License

This project was developed as a hackathon/prototype project.

Add an appropriate open-source license here if you intend to distribute the source under one.

⭐ Final Note

AI Finance Controller is built around a simple principle:

Automate what can be verified, investigate what is uncertain, and involve a human when the system cannot confidently resolve the financial decision.


---

## One important change from your existing README

Your **current README says this**:

> `anomaly_agent.py` trains a fresh IsolationForest on every pipeline run

But that is **no longer accurate for your current code**.

I checked your current ZIP, and your architecture now has:

```text
ml/train_anomaly_model.py
        ↓
trained model
        ↓
ml/models/
        ↓
anomaly_agent.py loads latest model
        ↓
prediction

So the new README correctly describes it as a trained + versioned ML model.

That's an important correction because a technical reviewer could otherwise ask:

"Why are you retraining your anomaly detector every API request?"

and your current implementation doesn't actually have that problem anymore.

What I would add next

Since this is going on GitHub for the Razorpay Buildathon, I'd make the top of the README even more impressive by adding screenshots/GIFs of your dashboard.

For example:

# AI Finance Controller

[ Dashboard Screenshot ]

AI-powered financial control tower...

Then:

## 🚀 Demo

[5-second GIF showing CSV upload → processing → results]

Then the architecture.

That makes the repo immediately understandable to a judge.

Also add a "Key Results" section

Right below the Solution section, something like:

## 📊 Key Results

| Capability | Result |
|---|---|
| Transactions processed | 100+ |
| Financial control stages | 8 |
| ML model | Isolation Forest |
| ML model | Trained + versioned |
| LLM investigation | Optional |
| Human escalation | Supported |
| Audit trail | Supported |
| CSV upload | Supported |
| Async processing | Supported |
| Automated tests | 33 |
| Docker | Supported |
| CI/CD | GitHub Actions |

But only put numerical accuracy/precision/F1 numbers in the README if they correspond to the final version of the model and evaluation code. Your ZIP contains a methodology correction compared with some of the older metrics we discussed, so I would not blindly copy the earlier 0.8 F1 numbers into the README.

Your README should ultimately tell this story:

Problem

Financial teams cannot manually investigate every settlement exception.

↓

Solution

AI Finance Controller creates an automated financial control layer.

↓

How

Rules + ML + LLM + multi-agent orchestration.

↓

Safety

Validation + risk scoring + independent LLM opinion + human escalation + audit trail.

↓

Engineering

FastAPI + Next.js + trained/versioned ML + database + Docker + tests + CI.

↓

Outcome

Routine transactions are cleared automatically, while ambiguous/high-risk cases are surfaced to humans with evidence.
