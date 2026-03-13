import { useState, useEffect, type ChangeEvent } from "react";
import { Cloud, Plus, Trash2, RefreshCw, ExternalLink, FileText, Upload, CheckCircle, XCircle, Search } from "lucide-react";
import toast from "react-hot-toast";
import { createBucket, listBuckets, deleteBucket, deleteAllBuckets, bulkCreateBuckets } from "../api";
import type { BucketCreatePayload, BulkBucketRow } from "../api";
import styles from "./S3Form.module.css";

const AWS_REGIONS = [
  "us-east-1", "us-east-2", "us-west-1", "us-west-2",
  "eu-west-1", "eu-west-2", "eu-central-1",
  "ap-south-1", "ap-southeast-1", "ap-southeast-2", "ap-northeast-1",
  "ca-central-1", "sa-east-1",
];

interface Bucket { name: string; created_at: string; }

export default function S3Form() {
  const [form, setForm] = useState<BucketCreatePayload>({
    bucket_name:  "",
    region:       "us-east-1",
    access_level: "private",
    versioning:   false,
    tags:         {},
    owner_email:  "",
  });

  const [tagKey, setTagKey]     = useState("");
  const [tagVal, setTagVal]     = useState("");
  const [loading, setLoading]   = useState(false);
  const [buckets, setBuckets]   = useState<Bucket[]>([]);
  const [listLoading, setListLoading]       = useState(false);
  const [deleteAllLoading, setDeleteAllLoading] = useState(false);
  const [lastResult, setLastResult]           = useState<any>(null);
  const [bucketSearch, setBucketSearch]       = useState("");

  // ── Bulk CSV state ──
  const [csvRows, setCsvRows]           = useState<BulkBucketRow[]>([]);
  const [bulkLoading, setBulkLoading]   = useState(false);
  const [bulkResults, setBulkResults]   = useState<any>(null);
  const [fileName, setFileName]         = useState("");

  const set = (k: keyof BucketCreatePayload, v: any) =>
    setForm((f) => ({ ...f, [k]: v }));

  const addTag = () => {
    if (!tagKey.trim()) return;
    setForm((f) => ({ ...f, tags: { ...f.tags, [tagKey]: tagVal } }));
    setTagKey(""); setTagVal("");
  };

  const removeTag = (k: string) => {
    const t = { ...form.tags }; delete t[k];
    setForm((f) => ({ ...f, tags: t }));
  };

  const handleCreate = async () => {
    if (!form.bucket_name.trim())   return toast.error("Bucket name is required.");
    if (!form.owner_email.trim())   return toast.error("Owner email is required.");

    const nameRegex = /^[a-z0-9][a-z0-9\-]{1,61}[a-z0-9]$/;
    if (!nameRegex.test(form.bucket_name)) {
      return toast.error(
        "Bucket name must be 3-63 chars, lowercase letters, numbers, hyphens only."
      );
    }

    setLoading(true);
    try {
      const { data } = await createBucket(form);
      setLastResult(data);
      toast.success(`Bucket "${form.bucket_name}" created!`);
      setForm((f) => ({ ...f, bucket_name: "", tags: {} }));
      handleList(); // auto-refresh bucket list
    } catch (err: any) {
      const detail = err.response?.data?.detail || "Failed to create bucket.";
      toast.error(detail);
      handleList(true); // refresh list — bucket may have been created before the error
    } finally {
      setLoading(false);
    }
  };

  const handleList = async (silent = false) => {
    setListLoading(true);
    try {
      const { data } = await listBuckets();
      setBuckets(data.buckets ?? []);
      if (!silent) toast.success(`Found ${data.count ?? data.buckets?.length ?? 0} bucket(s).`);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Could not reach backend. Is it running?");
    } finally {
      setListLoading(false);
    }
  };

  // Auto-load silently on mount
  useEffect(() => { handleList(true); }, []);

  // ── CSV parser ──
  const parseCSV = (text: string): BulkBucketRow[] => {
    const lines = text.trim().split("\n").filter(Boolean);
    if (lines.length < 2) return [];
    return lines.slice(1).map((line) => {
      const [bucket_name = "", region = "ap-south-1", access_level = "private", versioning = "false", owner_email = ""] =
        line.split(",").map((s) => s.trim());
      return { bucket_name, region, access_level, versioning: versioning.toLowerCase() === "true", owner_email };
    }).filter((r) => r.bucket_name);
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    setBulkResults(null);
    const reader = new FileReader();
    reader.onload = (ev) => {
      const rows = parseCSV(ev.target?.result as string);
      setCsvRows(rows);
      if (rows.length === 0) toast.error("No valid rows found in CSV.");
      else toast.success(`Parsed ${rows.length} bucket(s) from CSV.`);
    };
    reader.readAsText(file);
  };

  const handleBulkCreate = async () => {
    if (csvRows.length === 0) return toast.error("Upload a CSV file first.");
    setBulkLoading(true);
    setBulkResults(null);
    try {
      const { data } = await bulkCreateBuckets(csvRows);
      setBulkResults(data);
      toast.success(`✅ ${data.created} created, ❌ ${data.failed} failed.`);
      handleList();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Bulk create failed.");
    } finally {
      setBulkLoading(false);
    }
  };

  const handleDelete = async (name: string) => {
    if (!window.confirm(`Delete bucket "${name}"? This cannot be undone.`)) return;
    try {
      await deleteBucket(name, "");
      toast.success(`Bucket "${name}" deleted.`);
      setBuckets((b) => b.filter((x) => x.name !== name));
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to delete bucket.");
    }
  };

  const handleDeleteAll = async () => {
    if (buckets.length === 0) { toast.error("No buckets to delete."); return; }
    if (!window.confirm(`⚠️ Delete ALL ${buckets.length} buckets permanently? This CANNOT be undone!`)) return;
    setDeleteAllLoading(true);
    const tid = toast.loading(`Deleting ${buckets.length} buckets...`);
    try {
      const { data } = await deleteAllBuckets();
      toast.dismiss(tid);
      toast.success(`Deleted ${data.deleted} bucket${data.deleted !== 1 ? "s" : ""}.${data.failed ? ` ${data.failed} failed.` : ""}`);
      setBuckets([]);
    } catch (err: any) {
      toast.dismiss(tid);
      toast.error(err.response?.data?.detail || "Delete all failed.");
    } finally {
      setDeleteAllLoading(false);
    }
  };

  return (
    <>
    <div className={styles.wrapper}>
      {/* LEFT – Create Form */}
      <div className="card">
        <div className={styles.sectionHead}>
          <Cloud size={20} color="var(--primary)" />
          <h2>Create S3 Bucket</h2>
        </div>

        <div className="form-group">
          <label>Bucket Name *</label>
          <input
            placeholder="my-unique-bucket-name"
            value={form.bucket_name}
            onChange={(e) => set("bucket_name", e.target.value.toLowerCase())}
          />
        </div>

        <div className="form-group">
          <label>Owner Email *</label>
          <input
            type="email"
            placeholder="you@example.com"
            value={form.owner_email}
            onChange={(e) => set("owner_email", e.target.value)}
          />
        </div>

        <div className={styles.row2}>
          <div className="form-group">
            <label>AWS Region</label>
            <select value={form.region} onChange={(e) => set("region", e.target.value)}>
              {AWS_REGIONS.map((r) => <option key={r}>{r}</option>)}
            </select>
          </div>

          <div className="form-group">
            <label>Access Level</label>
            <select value={form.access_level} onChange={(e) => set("access_level", e.target.value)}>
              <option value="private">Private</option>
              <option value="public-read">Public Read</option>
            </select>
          </div>
        </div>

        <div className="toggle-row" style={{ marginBottom: 16 }}>
          <span style={{ fontSize: 14, fontWeight: 500 }}>Enable Versioning</span>
          <label className="toggle">
            <input
              type="checkbox"
              checked={form.versioning}
              onChange={(e) => set("versioning", e.target.checked)}
            />
            <span className="toggle-slider" />
          </label>
        </div>

        {/* Tags */}
        <div className="form-group">
          <label>Custom Tags</label>
          <div className={styles.tagRow}>
            <input placeholder="Key" value={tagKey} onChange={(e) => setTagKey(e.target.value)} style={{ flex: 1 }} />
            <input placeholder="Value" value={tagVal} onChange={(e) => setTagVal(e.target.value)} style={{ flex: 1 }} />
            <button className="btn btn-outline" onClick={addTag} style={{ flexShrink: 0 }}>
              <Plus size={14} /> Add
            </button>
          </div>
          {Object.keys(form.tags).length > 0 && (
            <div className={styles.tags}>
              {Object.entries(form.tags).map(([k, v]) => (
                <span key={k} className={styles.tag}>
                  {k}: {v}
                  <button onClick={() => removeTag(k)}>×</button>
                </span>
              ))}
            </div>
          )}
        </div>

        <button
          className="btn btn-primary"
          style={{ width: "100%", justifyContent: "center", height: 44 }}
          onClick={handleCreate}
          disabled={loading}
        >
          {loading ? <RefreshCw size={16} className={styles.spin} /> : <Cloud size={16} />}
          {loading ? "Creating Bucket…" : "Create S3 Bucket"}
        </button>

        {/* Result card */}
        {lastResult && (
          <div className={styles.resultCard}>
            <div className={styles.resultRow}>
              <span className="badge success">Created</span>
              <span style={{ fontWeight: 600 }}>{lastResult.bucket_url}</span>
              <a href={lastResult.bucket_url} target="_blank" rel="noreferrer">
                <ExternalLink size={14} />
              </a>
            </div>

          </div>
        )}
      </div>

      {/* RIGHT – Bucket List */}
      <div className="card">
        <div className={styles.sectionHead}>
          <Cloud size={20} color="var(--ml)" />
          <h2>Your Buckets</h2>
          <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
            <button className="btn btn-outline" onClick={() => void handleList()} disabled={listLoading}>
              {listLoading ? <RefreshCw size={14} className={styles.spin} /> : <RefreshCw size={14} />}
              Refresh
            </button>
            {buckets.length > 0 && (
              <button className="btn btn-danger" onClick={handleDeleteAll} disabled={deleteAllLoading}>
                {deleteAllLoading ? <RefreshCw size={14} className={styles.spin} /> : <Trash2 size={14} />}
                Delete All ({buckets.length})
              </button>
            )}
          </div>
        </div>

        {buckets.length > 0 && (
          <div className={styles.searchBar}>
            <Search size={14} color="var(--text-muted)" />
            <input
              className={styles.searchInput}
              type="text"
              placeholder="Search buckets…"
              value={bucketSearch}
              onChange={(e) => setBucketSearch(e.target.value)}
            />
          </div>
        )}

        {buckets.length === 0 ? (
          <div className={styles.empty}>
            <Cloud size={40} color="var(--border)" />
            <p>No buckets loaded yet.<br />Click Refresh to fetch from AWS.</p>
          </div>
        ) : (
          <div className={styles.bucketList}>
            {buckets.filter((b) => b.name.toLowerCase().includes(bucketSearch.toLowerCase())).map((b) => (
              <div key={b.name} className={styles.bucketItem}>
                <div>
                  <div style={{ fontWeight: 600 }}>{b.name}</div>
                  <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{b.created_at}</div>
                </div>
                <button className="btn btn-danger" onClick={() => handleDelete(b.name)}>
                  <Trash2 size={14} /> Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>

    {/* ── BULK CSV SECTION ── */}
    <div className="card" style={{ marginTop: 24 }}>
      <div className={styles.sectionHead}>
        <FileText size={20} color="var(--primary)" />
        <h2>Bulk Create from CSV</h2>
        <a
          href="/example_buckets.csv"
          download
          className="btn btn-outline"
          style={{ marginLeft: "auto", fontSize: 12 }}
        >
          ⬇ Download Example CSV
        </a>
      </div>

      {/* Drop zone */}
      <label className={styles.dropZone}>
        <input type="file" accept=".csv" onChange={handleFileChange} style={{ display: "none" }} />
        <Upload size={28} color="var(--primary)" />
        {fileName
          ? <span style={{ fontWeight: 600 }}>{fileName} — {csvRows.length} row(s) ready</span>
          : <span>Click to upload <strong>.csv</strong> file<br /><small style={{ color: "var(--text-muted)" }}>Format: bucket_name, region, access_level, versioning, owner_email</small></span>
        }
      </label>

      {/* Preview table */}
      {csvRows.length > 0 && (
        <div className={styles.csvTableWrap}>
          <table className={styles.csvTable}>
            <thead>
              <tr>
                <th>#</th><th>Bucket Name</th><th>Region</th><th>Access</th><th>Versioning</th><th>Email</th>
                {bulkResults && <th>Status</th>}
              </tr>
            </thead>
            <tbody>
              {csvRows.map((r, i) => {
                const res = bulkResults?.results?.[i];
                return (
                  <tr key={i}>
                    <td>{i + 1}</td>
                    <td><code>{r.bucket_name}</code></td>
                    <td>{r.region}</td>
                    <td>{r.access_level}</td>
                    <td>{r.versioning ? "Yes" : "No"}</td>
                    <td>{r.owner_email}</td>
                    {bulkResults && (
                      <td>
                        {res?.success
                          ? <span className={styles.ok}><CheckCircle size={14} /> Created</span>
                          : <span className={styles.fail} title={res?.message || ""}><XCircle size={14} /> {res?.message?.includes("already") ? "Already exists" : res?.message?.includes("Invalid") ? "Invalid name" : "Failed"}</span>
                        }
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Create button */}
      {csvRows.length > 0 && (
        <button
          className="btn btn-primary"
          style={{ marginTop: 16, height: 44, justifyContent: "center" }}
          onClick={handleBulkCreate}
          disabled={bulkLoading}
        >
          {bulkLoading
            ? <><RefreshCw size={16} className={styles.spin} /> Creating {csvRows.length} Buckets…</>
            : <><Upload size={16} /> Create All {csvRows.length} Buckets</>
          }
        </button>
      )}

      {/* Summary */}
      {bulkResults && (
        <div className={styles.bulkSummary}>
          <span className="badge success">✅ {bulkResults.created} Created</span>
          {bulkResults.failed > 0 && <span className="badge" style={{ background: "var(--error)" }}>❌ {bulkResults.failed} Failed</span>}
          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>out of {bulkResults.total} total</span>
        </div>
      )}
    </div>
    </>
  );
}
