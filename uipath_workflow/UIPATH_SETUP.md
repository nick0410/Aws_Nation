# UiPath — Bulk S3 Bucket Creator (Excel se AWS)

## Yeh Kya Karta Hai?

**Browser UI se fark:**

| Browser UI (`127.0.0.1:5173`) | UiPath Robot |
|---|---|
| Ek baar mein ek bucket | Ek CSV se 50+ buckets ek saath |
| User manually fill karta hai | Robot file padhta hai |
| Individual use | Office automation, scheduled batch jobs |

**Real use case:**
> 10 environments ke liye 10 S3 buckets chahiye → bas CSV mein naam likho → UiPath ek minute mein sab bana deta hai.

---

## Flow

```
   buckets_to_create.csv
   (bucket names, regions, emails)
          │
          ▼
   UiPath Robot padhta hai CSV
          │
          ▼
   POST http://127.0.0.1:8000/s3/bulk-create
          │
          ▼
   FastAPI → boto3 → AWS S3
          │
          ▼
   results_20260225_143000.csv  ← har bucket ka status
          │
          ▼
   Popup: "✅ 10 Created, ❌ 0 Failed"
```

---

## Setup (Ek Baar)

### 1. UiPath Studio Install karo
- Download: https://www.uipath.com/start-free (Community = free)

### 2. Project Open karo
```
File → Open → uipath_workflow/ → project.json
```

### 3. Packages Install karo (Manage Packages)
- `UiPath.WebAPI.Activities`
- `UiPath.Excel.Activities`
- `Newtonsoft.Json`

---

## Har Baar Use Karne Ka Tarika

### Step 1: CSV File Bharo
`uipath_workflow/buckets_to_create.csv` edit karo:
```csv
bucket_name,region,access_level,versioning,owner_email
my-prod-bucket-2026,ap-south-1,private,true,admin@company.com
my-staging-bucket,ap-south-1,private,false,dev@company.com
my-public-assets,ap-south-1,public-read,false,cdn@company.com
```

### Step 2: Backend Chalao
```powershell
Set-Location "c:\Users\KIIT0001\Desktop\aws_autonation\backend"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### Step 3: UiPath mein F5 dabaao
- Robot CSV ka path poochega
- Confirm: "10 buckets banane hain?" → OK
- Sab kuch automatic

### Step 4: Results File
`results_YYYYMMDD_HHMMSS.csv` same folder mein ban jaati hai

---

## Aur Kya Kar Sakte Ho UiPath Se

1. **Scheduled batch** — Task Scheduler se roz raat ko robot chalaao
2. **Excel report** — bucket list pull karke Excel mein save karo
3. **Cleanup bot** — CSV mein old names, robot delete kare
4. **Notification** — bucket banne pe Outlook mail bhej de

---

## Old Content (Replaced)

```
   UiPath Robot
       │
       │  Pops up dialog boxes → user fills form
       │
       ▼
   HTTP POST → FastAPI Backend (:8000)
                    │
                    ├── boto3   → AWS S3 (create bucket)
                    ├── BART    → AI summary
                    └── Web3.py → Ethereum (log on-chain)
```

UiPath acts as the **attended automation trigger** — it shows input dialogs,
collects user data, calls our REST API, and displays results — all without
the user opening a browser.

---

## Prerequisites

1. **UiPath Studio** (free Community Edition)  
   Download: https://www.uipath.com/start-free

2. **FastAPI backend running** on `http://localhost:8000`
   ```bash
   cd backend
   python main.py
   ```

---

## Step-by-Step: Running the Workflow

### 1. Install UiPath Studio

- Download from https://www.uipath.com/start-free
- Sign up with a free Community license
- Install and open UiPath Studio

### 2. Open the Project

1. In UiPath Studio → **File** → **Open**
2. Navigate to: `aws_autonation/uipath_workflow/`
3. Select `project.json`
4. Studio will load `CreateS3Bucket.xaml`

### 3. Install Required Packages

In UiPath Studio:
1. Go to **Manage Packages** (Tools menu or Ctrl+Shift+P)
2. Search and install:
   - `UiPath.WebAPI.Activities` → version 1.16+
   - `Newtonsoft.Json` → already bundled usually

### 4. Run the Workflow

Press **F5** or click **Run** — you'll see:

```
┌─────────────────────────────────────┐
│  AWS AutoNation – Create S3 Bucket  │
│                                     │
│  S3 Bucket Name:  [_____________]   │
│                                     │
│             [OK]  [Cancel]          │
└─────────────────────────────────────┘
```

Then:
1. Enter your bucket name (e.g. `john-store-2026`)
2. Enter your email
3. Select AWS region
4. Select access level (private / public-read)

**Result dialog:**
```
✅ S3 Bucket Created Successfully!

📦 Bucket: john-store-2026
🌐 URL: https://john-store-2026.s3.amazonaws.com
🌍 Region: ap-south-1

⛓️ Blockchain TX: 0x4a2f...8c91
```

---

## Workflow Structure

```
CreateS3Bucket.xaml
│
├── Step 1: Get User Inputs
│   ├── InputDialog → Bucket Name
│   ├── InputDialog → Owner Email
│   ├── SelectItemDialog → AWS Region
│   └── SelectItemDialog → Access Level
│
├── Step 2: Build JSON Payload
│   └── Assign → requestBody string
│
├── Step 3: HTTP POST to FastAPI
│   └── HTTPRequest → POST http://localhost:8000/s3/create
│
└── Step 4: Show Result
    ├── Parse JSON response
    ├── If success → MessageBox (bucket URL + TX hash)
    └── If error  → MessageBox (error details)
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Cannot connect to backend` | Start FastAPI: `python main.py` in backend folder |
| `UiPath.WebAPI not found` | Go to Manage Packages → install `UiPath.WebAPI.Activities` |
| `AccessDenied from AWS` | Check your `.env` AWS keys and IAM permissions |
| Dialogs don't appear | Enable `Attended` process profile in project settings |

---

## Running Without UiPath (Web UI)

If UiPath Studio is not installed, the same functionality is available in the **React web UI**:
```bash
cd frontend
npm run dev
# Open http://localhost:5173
```
