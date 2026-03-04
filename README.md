# AWS AutoNation

> **Automate AWS S3 buckets from a UI · AI-powered product summaries · Cost prediction**

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        React UI (Vite)                          │
│  [S3 Tab]  ──────────────────────────────────  [ML Tab]         │
│  Create / List / Delete S3 buckets              AI Summarizer   │
│  [Cost Tab]  ─  Predict monthly S3 costs                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP (axios)
                      ──────▼──────
                     │  FastAPI API │  :8000
                      ─────────────
                      /             \
                     ▼               ▼
               boto3              BART
               (AWS)              (ML)
                 │                  │
            S3 Bucket          HuggingFace
            Creation             Model
```

---

## Features

| Feature | Technology | What it does |
|---------|-----------|--------------|
| S3 Automation | AWS boto3 | Create buckets with 1 form fill: name, region, ACL, versioning, custom tags |
| AI Summary | HuggingFace BART | Paste a long product description → get a concise AI-generated summary |
| Cost Predictor | Custom estimation | Predict monthly S3 costs across storage classes |

---

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure credentials
copy .env.example .env
# Edit .env: fill AWS keys

# Start API server
python main.py
# → API running at http://localhost:8000
# → Swagger docs at http://localhost:8000/docs
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
# → UI running at http://localhost:5173
```

---

## Environment Variables

Create `backend/.env` (copy from `.env.example`):

```env
# AWS
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
```

---

## API Reference

| Method | Endpoint           | Description                    |
|--------|--------------------|--------------------------------|
| POST   | `/s3/create`       | Create S3 bucket               |
| GET    | `/s3/list`         | List all buckets               |
| DELETE | `/s3/delete`       | Delete a bucket                |
| POST   | `/ml/summarize`    | Generate product AI summary    |
| POST   | `/s3/cost-estimate`| Estimate monthly S3 costs      |
| GET    | `/health`          | Health check                   |
| GET    | `/docs`            | Swagger UI                     |

---

## Project Structure

```
aws_autonation/
├── backend/
│   ├── main.py              ← FastAPI app + all routes
│   ├── aws_service.py       ← boto3 S3 operations
│   ├── ml_service.py        ← HuggingFace BART summarizer
│   ├── cost_service.py      ← S3 cost estimation
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── App.tsx          ← Tab-based layout
│       ├── api.ts           ← Axios API client
│       └── components/
│           ├── Header.tsx
│           ├── S3Form.tsx       ← Bucket creation UI
│           ├── BucketSummary.tsx ← Bucket analytics
│           └── CostPredictor.tsx ← Cost estimation UI
```

---

## ML Model Details

- **Model:** `facebook/bart-large-cnn` (HuggingFace Transformers)
- **Task:** Abstractive text summarization
- **Fallback:** Extractive summarization (no internet needed) if model unavailable
- **First run:** Downloads ~1.5GB model weights (cached after that)
