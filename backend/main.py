"""
AWS AutoNation - Main FastAPI Application
Endpoints: S3 automation, ML Product Summary, Blockchain Logging
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import time

from aws_service import create_s3_bucket, list_user_buckets, delete_s3_bucket
from ml_service import generate_product_summary
from blockchain_service import log_bucket_creation, get_bucket_logs, get_contract_info
from cost_service import estimate_cost
from auth_service import signup as auth_signup, login as auth_login, get_user_from_token, logout as auth_logout

# ── In-memory TTL caches ──────────────────────────────────────────────
LIST_CACHE:    dict = {"data": None, "ts": 0.0}   # TTL 30s
SUMMARY_CACHE: dict = {"data": None, "ts": 0.0}   # TTL 300s
LIST_TTL    = 30
SUMMARY_TTL = 300

app = FastAPI(
    title="AWS AutoNation API",
    description="Automate S3 bucket creation, generate product summaries via ML, and log events on blockchain",
    version="1.0.0"
)

# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Auth helper
# ─────────────────────────────────────────────

def _get_current_user(request: Request) -> dict:
    """Extract user from Authorization header. Returns user dict with AWS creds."""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated. Please log in.")
    user = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    return user


# ─────────────────────────────────────────────
# Auth Models
# ─────────────────────────────────────────────

class SignupRequest(BaseModel):
    username: str
    password: str
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "ap-south-1"

class LoginRequest(BaseModel):
    username: str
    password: str


# ─────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────

class BucketCreateRequest(BaseModel):
    bucket_name: str
    region: str = "us-east-1"
    access_level: str = "private"          # private | public-read
    versioning: bool = False
    tags: Optional[dict] = {}
    owner_email: str

class BucketDeleteRequest(BaseModel):
    bucket_name: str
    region: str = "us-east-1"

class ProductSummaryRequest(BaseModel):
    product_name: str
    product_description: str
    max_length: int = 130
    min_length: int = 30

class BlockchainLogRequest(BaseModel):
    bucket_name: str
    owner_email: str
    region: str

class BulkBucketItem(BaseModel):
    bucket_name: str
    region: str = "ap-south-1"
    access_level: str = "private"
    versioning: bool = False
    owner_email: str
    tags: Optional[dict] = {}

class BulkBucketCreateRequest(BaseModel):
    buckets: list[BulkBucketItem]


# ─────────────────────────────────────────────
# Root
# ─────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "message": "AWS AutoNation API is running",
        "docs": "/docs",
        "version": "1.0.0"
    }


# ─────────────────────────────────────────────
# Auth Routes
# ─────────────────────────────────────────────

@app.post("/auth/signup")
async def signup(req: SignupRequest):
    result = auth_signup(
        username=req.username,
        password=req.password,
        aws_access_key_id=req.aws_access_key_id,
        aws_secret_access_key=req.aws_secret_access_key,
        aws_region=req.aws_region,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/auth/login")
async def login(req: LoginRequest):
    result = auth_login(username=req.username, password=req.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return result


@app.post("/auth/logout")
async def logout(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    return auth_logout(token)


@app.get("/auth/me")
async def get_me(request: Request):
    user = _get_current_user(request)
    return {"username": user["username"], "aws_region": user["aws_region"]}


# ─────────────────────────────────────────────
# S3 Routes
# ─────────────────────────────────────────────

@app.post("/s3/create")
async def create_bucket(req: BucketCreateRequest, request: Request):
    """
    Create an S3 bucket with full configuration.
    After creation, automatically logs the event on blockchain.
    """
    user = _get_current_user(request)
    result = create_s3_bucket(
        bucket_name=req.bucket_name,
        region=req.region,
        access_level=req.access_level,
        versioning=req.versioning,
        tags=req.tags,
        owner_email=req.owner_email,
        access_key=user["aws_access_key_id"],
        secret_key=user["aws_secret_access_key"],
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    # Invalidate list cache so next fetch is fresh
    LIST_CACHE["data"] = None
    LIST_CACHE["ts"]   = 0.0

    # Auto-log to blockchain after successful bucket creation
    blockchain_result = log_bucket_creation(
        bucket_name=req.bucket_name,
        owner_email=req.owner_email,
        region=req.region
    )

    return {
        "success": True,
        "message": f"Bucket '{req.bucket_name}' created successfully!",
        "bucket_url": result["bucket_url"],
        "region": req.region,
        "access_level": req.access_level,
        "versioning": req.versioning,
        "blockchain": blockchain_result
    }


@app.get("/s3/list")
async def list_buckets(request: Request):
    """List all S3 buckets in the AWS account (cached 30 s)."""
    user = _get_current_user(request)
    if LIST_CACHE["data"] and (time.time() - LIST_CACHE["ts"]) < LIST_TTL:
        return LIST_CACHE["data"]
    result = list_user_buckets(
        access_key=user["aws_access_key_id"],
        secret_key=user["aws_secret_access_key"],
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    LIST_CACHE["data"] = result
    LIST_CACHE["ts"]   = time.time()
    return result


@app.delete("/s3/delete")
async def delete_bucket(req: BucketDeleteRequest, request: Request):
    """Delete an existing S3 bucket."""
    user = _get_current_user(request)
    result = delete_s3_bucket(
        req.bucket_name, req.region,
        access_key=user["aws_access_key_id"],
        secret_key=user["aws_secret_access_key"],
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    LIST_CACHE["data"] = None; LIST_CACHE["ts"] = 0.0
    SUMMARY_CACHE["data"] = None; SUMMARY_CACHE["ts"] = 0.0
    return result


@app.delete("/s3/delete-all")
async def delete_all_buckets(request: Request):
    """Delete ALL buckets in the AWS account concurrently."""
    user = _get_current_user(request)
    from aws_service import list_user_buckets
    import asyncio

    list_result = list_user_buckets(
        access_key=user["aws_access_key_id"],
        secret_key=user["aws_secret_access_key"],
    )
    bucket_names = [b["name"] for b in list_result.get("buckets", [])]

    if not bucket_names:
        return {"deleted": 0, "failed": 0, "results": []}

    loop = asyncio.get_event_loop()
    results = []

    async def _del(name):
        r = await loop.run_in_executor(
            None,
            lambda: delete_s3_bucket(
                name, "",
                access_key=user["aws_access_key_id"],
                secret_key=user["aws_secret_access_key"],
            )
        )
        return {"bucket": name, **r}

    tasks = [_del(n) for n in bucket_names]
    results = await asyncio.gather(*tasks)

    deleted = sum(1 for r in results if r.get("success"))
    failed  = len(results) - deleted
    LIST_CACHE["data"] = None; LIST_CACHE["ts"] = 0.0
    SUMMARY_CACHE["data"] = None; SUMMARY_CACHE["ts"] = 0.0
    return {"deleted": deleted, "failed": failed, "results": list(results)}


@app.post("/s3/bulk-create")
async def bulk_create_buckets(req: BulkBucketCreateRequest, request: Request):
    """
    Create multiple S3 buckets in one call.
    UiPath reads an Excel file and sends all rows here.
    Returns per-bucket success/failure so the robot can log results back to Excel.
    """
    user = _get_current_user(request)
    results = []
    success_count = 0
    fail_count = 0

    for item in req.buckets:
        r = create_s3_bucket(
            bucket_name=item.bucket_name,
            region=item.region,
            access_level=item.access_level,
            versioning=item.versioning,
            tags=item.tags or {},
            owner_email=item.owner_email,
            access_key=user["aws_access_key_id"],
            secret_key=user["aws_secret_access_key"],
        )
        if r["success"]:
            success_count += 1
            log_bucket_creation(item.bucket_name, item.owner_email, item.region)
        else:
            fail_count += 1

        results.append({
            "bucket_name": item.bucket_name,
            "region": item.region,
            "owner_email": item.owner_email,
            "success": r["success"],
            "message": r.get("bucket_url", r.get("error", "unknown"))
        })

    return {
        "total": len(req.buckets),
        "created": success_count,
        "failed": fail_count,
        "results": results
    }


# ─────────────────────────────────────────────
# Bucket Summary Route
# ─────────────────────────────────────────────

@app.get("/s3/summary")
async def bucket_summary_all(request: Request, bucket_name: str = "", detail: bool = False):
    """
    Fast summary: file types + size per bucket (1 AWS call per bucket).
    Pass detail=true to also fetch versioning + Lambda triggers (3 calls per bucket).
    All-buckets result is cached 300 s.
    """
    user = _get_current_user(request)
    import asyncio
    from aws_service import get_s3_client, _detect_bucket_region, list_user_buckets as _list
    from concurrent.futures import ThreadPoolExecutor
    from collections import Counter

    if not bucket_name:
        if SUMMARY_CACHE["data"] and (time.time() - SUMMARY_CACHE["ts"]) < SUMMARY_TTL:
            return SUMMARY_CACHE["data"]

    def _summarize(name: str) -> dict:
        try:
            region = _detect_bucket_region(name, access_key=user["aws_access_key_id"], secret_key=user["aws_secret_access_key"])
            client = get_s3_client(region, access_key=user["aws_access_key_id"], secret_key=user["aws_secret_access_key"])

            # Objects + file types  (1 fast API call)
            object_count = 0
            total_size   = 0
            ext_counter: Counter = Counter()
            try:
                resp = client.list_objects_v2(Bucket=name, MaxKeys=1000)
                for obj in resp.get("Contents", []):
                    object_count += 1
                    total_size   += obj.get("Size", 0)
                    key      = obj.get("Key", "")
                    filename = key.split("/")[-1]
                    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "(no ext)"
                    ext_counter[ext] += 1
            except Exception:
                pass

            # Optional: versioning + Lambda (only when detail=True or single-bucket)
            versioning = None
            lambdas    = []
            if detail or bucket_name:
                try:
                    v = client.get_bucket_versioning(Bucket=name)
                    versioning = v.get("Status") == "Enabled"
                except Exception:
                    versioning = False
                try:
                    notif = client.get_bucket_notification_configuration(Bucket=name)
                    for cfg in notif.get("LambdaFunctionConfigurations", []):
                        arn = cfg.get("LambdaFunctionArn", "")
                        fn  = arn.split(":")[-1] if arn else ""
                        if fn:
                            lambdas.append({"function": fn, "arn": arn,
                                            "events": cfg.get("Events", [])})
                except Exception:
                    pass

            return {
                "name":             name,
                "region":           region,
                "versioning":       versioning,
                "object_count":     object_count,
                "total_size_bytes": total_size,
                "total_size_mb":    round(total_size / (1024 * 1024), 3),
                "file_types":       [{"ext": e, "count": c}
                                     for e, c in ext_counter.most_common(10)],
                "lambda_triggers":  lambdas,
            }
        except Exception as ex:
            return {"name": name, "region": "unknown", "error": str(ex),
                    "object_count": 0, "total_size_mb": 0,
                    "file_types": [], "lambda_triggers": [], "versioning": None}

    targets = [bucket_name] if bucket_name else \
              [b["name"] for b in _list(
                  access_key=user["aws_access_key_id"],
                  secret_key=user["aws_secret_access_key"],
              ).get("buckets", [])]

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=30) as pool:
        results = await asyncio.gather(
            *[loop.run_in_executor(pool, _summarize, n) for n in targets]
        )

    payload = {"buckets": list(results), "total": len(results)}

    if not bucket_name:
        SUMMARY_CACHE["data"] = payload
        SUMMARY_CACHE["ts"]   = time.time()

    return payload


# ─────────────────────────────────────────────# Cost Estimation Routes
# ─────────────────────────────────────────────

class CostEstimateRequest(BaseModel):
    bucket_name:            str = ""
    storage_gb:             float = 10.0
    put_requests_per_day:   int   = 100
    get_requests_per_day:   int   = 500
    transfer_out_gb_month:  float = 1.0
    versioning_enabled:     bool  = False
    object_count:           int   = 0


@app.post("/s3/cost-estimate")
async def cost_estimate(req: CostEstimateRequest, request: Request):
    """
    Estimate monthly S3 cost across storage classes.
    If bucket_name provided, auto-fetches versioning status from AWS.
    """
    user = _get_current_user(request)
    import boto3, os
    from dotenv import load_dotenv
    load_dotenv()

    versioning = req.versioning_enabled
    object_count = req.object_count

    # Auto-detect versioning from real bucket if name given
    if req.bucket_name:
        try:
            from aws_service import get_s3_client, _detect_bucket_region
            region = _detect_bucket_region(req.bucket_name, access_key=user["aws_access_key_id"], secret_key=user["aws_secret_access_key"])
            client = get_s3_client(region, access_key=user["aws_access_key_id"], secret_key=user["aws_secret_access_key"])

            ver_resp = client.get_bucket_versioning(Bucket=req.bucket_name)
            versioning = ver_resp.get("Status") == "Enabled"

            # Count objects for monitoring cost estimate
            if object_count == 0:
                paginator = client.get_paginator("list_objects_v2")
                count = 0
                for page in paginator.paginate(Bucket=req.bucket_name, PaginationConfig={"MaxItems": 10000}):
                    count += page.get("KeyCount", 0)
                object_count = count
        except Exception:
            pass  # Use request values if bucket lookup fails

    result = estimate_cost(
        storage_gb=req.storage_gb,
        put_requests_per_day=req.put_requests_per_day,
        get_requests_per_day=req.get_requests_per_day,
        transfer_out_gb_month=req.transfer_out_gb_month,
        versioning_enabled=versioning,
        object_count=object_count,
    )
    return result


# ─────────────────────────────────────────────# ML Routes
# ─────────────────────────────────────────────

@app.post("/ml/summarize")
async def summarize_product(req: ProductSummaryRequest):
    """
    Generate an AI-powered product summary using HuggingFace BART model.
    """
    result = generate_product_summary(
        product_name=req.product_name,
        product_description=req.product_description,
        max_length=req.max_length,
        min_length=req.min_length
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    return {
        "success": True,
        "product_name": req.product_name,
        "original_length": len(req.product_description.split()),
        "summary": result["summary"],
        "model_used": result["model_used"]
    }


# ─────────────────────────────────────────────
# Blockchain Routes
# ─────────────────────────────────────────────

@app.get("/blockchain/logs")
async def get_logs():
    """Fetch all bucket creation logs from the blockchain."""
    result = get_bucket_logs()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@app.get("/blockchain/info")
async def contract_info():
    """Get smart contract metadata."""
    result = get_contract_info()
    return result


# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "healthy", "service": "AWS AutoNation"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
