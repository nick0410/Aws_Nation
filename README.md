# AWS AutoNation

> **Automate AWS S3 buckets from a UI · AI-powered product summaries · Immutable blockchain audit trail**

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        React UI (Vite)                          │
│  [S3 Tab]  ──────────────────────────────────  [ML Tab]         │
│  Create / List / Delete S3 buckets              AI Summarizer   │
│  [Blockchain Tab]  ─  View on-chain bucket logs                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP (axios)
                      ──────▼──────
                     │  FastAPI API │  :8000
                      ─────────────
                      /       |       \
                     ▼        ▼        ▼
               boto3       BART     Web3.py
               (AWS)       (ML)   (Ethereum)
                 │           │         │
            S3 Bucket    HuggingFace  Sepolia
            Creation      Model      Testnet
```

---

## Features

| Feature | Technology | What it does |
|---------|-----------|--------------|
| S3 Automation | AWS boto3 | Create buckets with 1 form fill: name, region, ACL, versioning, custom tags |
| AI Summary | HuggingFace BART | Paste a long product description → get a concise AI-generated summary |
| Blockchain Log | Ethereum Sepolia | Every bucket creation is immutably recorded on-chain with tx hash |

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
# Edit .env: fill AWS keys + blockchain settings

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

### 3. Smart Contract Deployment (Blockchain)

1. Open [https://remix.ethereum.org](https://remix.ethereum.org)
2. Paste `smart_contract/BucketLogger.sol`
3. Compile → Solidity 0.8.20
4. Deploy to **Sepolia testnet** via MetaMask
5. Copy the deployed contract address → set as `BLOCKCHAIN_CONTRACT_ADDRESS` in `.env`

---

## Environment Variables

Create `backend/.env` (copy from `.env.example`):

```env
# AWS
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1

# Blockchain (Ethereum Sepolia)
BLOCKCHAIN_RPC_URL=https://sepolia.infura.io/v3/YOUR_PROJECT_ID
BLOCKCHAIN_PRIVATE_KEY=your_wallet_private_key
BLOCKCHAIN_CONTRACT_ADDRESS=0x...deployed_contract_address
```

> **Note:** The app works without blockchain configured – bucket creation still works, blockchain logging is skipped gracefully.

---

## API Reference

| Method | Endpoint           | Description                    |
|--------|--------------------|--------------------------------|
| POST   | `/s3/create`       | Create S3 bucket               |
| GET    | `/s3/list`         | List all buckets               |
| DELETE | `/s3/delete`       | Delete a bucket                |
| POST   | `/ml/summarize`    | Generate product AI summary    |
| GET    | `/blockchain/logs` | Fetch all on-chain bucket logs |
| GET    | `/blockchain/info` | Smart contract status          |
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
│   ├── blockchain_service.py← Web3.py Ethereum logging
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── App.tsx          ← Tab-based layout
│       ├── api.ts           ← Axios API client
│       └── components/
│           ├── Header.tsx
│           ├── S3Form.tsx   ← Bucket creation UI
│           ├── MLSummary.tsx← AI summarization UI
│           └── BlockchainLogs.tsx ← On-chain audit UI
└── smart_contract/
    └── BucketLogger.sol     ← Ethereum smart contract
```

---

## ML Model Details

- **Model:** `facebook/bart-large-cnn` (HuggingFace Transformers)
- **Task:** Abstractive text summarization
- **Fallback:** Extractive summarization (no internet needed) if model unavailable
- **First run:** Downloads ~1.5GB model weights (cached after that)

---

## Blockchain Contract

```solidity
// Stores for every bucket:
struct BucketLog {
    string  bucketName;
    string  ownerEmail;
    string  region;
    uint256 timestamp;
    address creator;
}
```

- Network: **Ethereum Sepolia Testnet**
- Explorer: `https://sepolia.etherscan.io`
- Get free Sepolia ETH: `https://sepoliafaucet.com`
