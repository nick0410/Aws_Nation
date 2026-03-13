import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  (import.meta.env.DEV ? "http://127.0.0.1:8000" : "/api");

const API = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Attach auth token to every request
API.interceptors.request.use((config) => {
  const stored = localStorage.getItem("autonation_user");
  if (stored) {
    try {
      const user = JSON.parse(stored);
      if (user.token) {
        config.headers.Authorization = `Bearer ${user.token}`;
      }
    } catch {
      // ignore
    }
  }
  return config;
});

// ── S3 ──────────────────────────────────────────────────────
export interface BucketCreatePayload {
  bucket_name:  string;
  region:       string;
  access_level: string;
  versioning:   boolean;
  tags:         Record<string, string>;
  owner_email:  string;
}

export const createBucket   = (data: BucketCreatePayload) => API.post("/s3/create", data);
export const listBuckets    = ()                           => API.get("/s3/list");
export const deleteBucket    = (bucket_name: string, region: string) =>
  API.delete("/s3/delete", { data: { bucket_name, region } });
export const deleteAllBuckets = () => API.delete("/s3/delete-all");

export interface BulkBucketRow {
  bucket_name:  string;
  region:       string;
  access_level: string;
  versioning:   boolean;
  owner_email:  string;
  tags?:        Record<string, string>;
}
export const bulkCreateBuckets = (buckets: BulkBucketRow[]) =>
  API.post("/s3/bulk-create", { buckets });

// ── Bucket Summary ───────────────────────────────────────────
export const getBucketSummary  = (bucket_name = "") =>
  API.get("/s3/summary", { params: { ...(bucket_name ? { bucket_name } : {}), detail: true } });

// ── Cost Estimator ───────────────────────────────────────────
export interface CostEstimatePayload {
  bucket_name?:           string;
  storage_gb:             number;
  put_requests_per_day:   number;
  get_requests_per_day:   number;
  transfer_out_gb_month:  number;
  versioning_enabled?:    boolean;
  object_count?:          number;
}
export const estimateCost = (data: CostEstimatePayload) => API.post("/s3/cost-estimate", data);

// ── ML Summary ───────────────────────────────────────────────
export interface ProductSummaryPayload {
  product_name: string;
  product_description: string;
  max_length?: number;
  min_length?: number;
}

export const summarizeProduct = (data: ProductSummaryPayload) => API.post("/ml/summarize", data);

export default API;
