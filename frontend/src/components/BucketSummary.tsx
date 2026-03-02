import { useState, useMemo } from "react";
import { RefreshCw, Search, ChevronDown, ChevronRight, FileText, Zap, Database } from "lucide-react";
import toast from "react-hot-toast";
import { getBucketSummary } from "../api";
import styles from "./BucketSummary.module.css";

interface FileType  { ext: string; count: number; }
interface LambdaTrigger { function: string; arn: string; events: string[]; }

interface BucketInfo {
  name:             string;
  region:           string;
  versioning:       boolean;
  object_count:     number;
  total_size_mb:    number;
  file_types:       FileType[];
  lambda_triggers:  LambdaTrigger[];
  error?:           string;
}

function fmtSize(mb: number): string {
  if (mb === 0)      return "0 B";
  if (mb < 0.001)    return `${Math.round(mb * 1024 * 1024)} B`;
  if (mb < 1)        return `${(mb * 1024).toFixed(1)} KB`;
  if (mb < 1024)     return `${mb.toFixed(2)} MB`;
  return `${(mb / 1024).toFixed(2)} GB`;
}

const EXT_COLORS: Record<string, string> = {
  pdf:  "#e84393", jpg: "#f59e0b", jpeg: "#f59e0b", png: "#10b981",
  gif:  "#8b5cf6", mp4: "#3b82f6", mov: "#3b82f6", mp3: "#06b6d4",
  csv:  "#22c55e", json: "#f97316", xml: "#84cc16", txt: "#94a3b8",
  zip:  "#f43f5e", tar: "#f43f5e", gz:  "#f43f5e", py:  "#facc15",
  js:   "#fbbf24", ts:  "#3b82f6", html:"#f97316", css: "#a78bfa",
  log:  "#6b7280", sql: "#38bdf8", yaml:"#86efac",
};

export default function BucketSummary() {
  const [buckets,   setBuckets]   = useState<BucketInfo[]>([]);
  const [loading,   setLoading]   = useState(false);
  const [scanned,   setScanned]   = useState(false);
  const [search,    setSearch]    = useState("");
  const [expanded,  setExpanded]  = useState<Record<string, boolean>>({});
  const [lastFetch, setLastFetch] = useState<Date | null>(null);

  const fetchAll = async () => {
    setLoading(true);
    setBuckets([]);
    try {
      const { data } = await getBucketSummary();
      setBuckets(data.buckets || []);
      setLastFetch(new Date());
      setScanned(true);
      toast.success(`Loaded ${data.total} buckets`);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to fetch summary.");
    } finally {
      setLoading(false);
    }
  };

  const filtered = useMemo(() =>
    buckets.filter(b => b.name.toLowerCase().includes(search.toLowerCase()) ||
                        b.region?.toLowerCase().includes(search.toLowerCase())),
    [buckets, search]
  );

  const toggleExpand = (name: string) =>
    setExpanded(e => ({ ...e, [name]: !e[name] }));

  // Summary stats
  const stats = useMemo(() => ({
    totalObjects:  buckets.reduce((s, b) => s + (b.object_count || 0), 0),
    totalSizeMb:   buckets.reduce((s, b) => s + (b.total_size_mb || 0), 0),
    lambdaCount:   buckets.reduce((s, b) => s + (b.lambda_triggers?.length || 0), 0),
    versionedCount:buckets.filter(b => b.versioning).length,
  }), [buckets]);

  const allExts = useMemo(() => {
    const c: Record<string, number> = {};
    buckets.forEach(b => b.file_types?.forEach(f => { c[f.ext] = (c[f.ext]||0) + f.count; }));
    return Object.entries(c).sort((a,b) => b[1]-a[1]).slice(0,8);
  }, [buckets]);

  return (
    <div className={styles.wrap}>
      {/* Header */}
      <div className={styles.pageHeader}>
        <div className={styles.pageIcon}><Database size={28} /></div>
        <div>
          <h1 className={styles.pageTitle}>Bucket Summary</h1>
          <p className={styles.pageSub}>
            Real-time breakdown — file types stored, Lambda triggers & storage usage across all S3 buckets.
          </p>
        </div>
      </div>

      {/* Stats row */}
      {buckets.length > 0 && (
        <div className={styles.statsRow}>
          <div className={styles.stat}>
            <span className={styles.statVal}>{buckets.length}</span>
            <span className={styles.statLbl}>Buckets</span>
          </div>
          <div className={styles.stat}>
            <span className={styles.statVal}>{stats.totalObjects.toLocaleString()}</span>
            <span className={styles.statLbl}>Total Objects</span>
          </div>
          <div className={styles.stat}>
            <span className={styles.statVal}>{fmtSize(stats.totalSizeMb)}</span>
            <span className={styles.statLbl}>Total Storage</span>
          </div>
          <div className={styles.stat}>
            <span className={styles.statVal}>{stats.lambdaCount}</span>
            <span className={styles.statLbl}>Lambda Triggers</span>
          </div>
          <div className={styles.stat}>
            <span className={styles.statVal}>{stats.versionedCount}</span>
            <span className={styles.statLbl}>Versioned</span>
          </div>
        </div>
      )}

      {/* File type overview */}
      {allExts.length > 0 && (
        <div className="card">
          <div className={styles.sectionHead}>
            <FileText size={16} />
            <h2>File Types Across All Buckets</h2>
          </div>
          <div className={styles.extRow}>
            {allExts.map(([ext, cnt]) => (
              <div key={ext} className={styles.extPill}
                   style={{ "--ext-color": EXT_COLORS[ext] || "#6b7280" } as any}>
                <span className={styles.extDot} />
                <span className={styles.extName}>.{ext}</span>
                <span className={styles.extCnt}>{cnt}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Controls */}
      <div className={styles.controls}>
        <div className={styles.searchWrap}>
          <Search size={14} className={styles.searchIcon} />
          <input
            className={styles.searchInput}
            placeholder="Search buckets by name or region…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            disabled={!scanned}
          />
        </div>
        <button className={`btn ${styles.refreshBtn}`} onClick={fetchAll} disabled={loading}>
          <RefreshCw size={14} className={loading ? styles.spin : ""} />
          {loading ? "Scanning…" : scanned ? "Refresh" : "Scan Buckets"}
        </button>
        {lastFetch && (
          <span className={styles.lastFetch}>
            Last updated: {lastFetch.toLocaleTimeString()}
          </span>
        )}
      </div>

      {/* Bucket table */}
      {!scanned && !loading ? (
        <div className={styles.idleState}>
          <Database size={40} className={styles.idleIcon} />
          <p>Click <strong>Scan Buckets</strong> to load file types, storage usage &amp; Lambda triggers across all your S3 buckets.</p>
        </div>
      ) : loading && buckets.length === 0 ? (
        <div className={styles.loader}>
          <RefreshCw size={22} className={styles.spin} />
          <span>Scanning all buckets… this may take a moment.</span>
        </div>
      ) : filtered.length === 0 ? (
        <div className={styles.empty}>No buckets match your search.</div>
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th style={{ width: 32 }}></th>
                <th>Bucket Name</th>
                <th>Region</th>
                <th>Objects</th>
                <th>Size</th>
                <th>Top File Types</th>
                <th>Lambda Triggers</th>
                <th>Versioning</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(b => {
                const isOpen = !!expanded[b.name];
                return (
                  <>
                    <tr key={b.name}
                        className={`${styles.row} ${isOpen ? styles.rowOpen : ""} ${b.error ? styles.rowError : ""}`}
                        onClick={() => toggleExpand(b.name)}>
                      <td className={styles.chevronCell}>
                        {isOpen
                          ? <ChevronDown  size={14} />
                          : <ChevronRight size={14} />}
                      </td>
                      <td className={styles.nameCell}>{b.name}</td>
                      <td><span className={styles.regionBadge}>{b.region}</span></td>
                      <td className={styles.numCell}>{b.object_count?.toLocaleString() ?? "—"}</td>
                      <td className={styles.numCell}>{fmtSize(b.total_size_mb)}</td>
                      <td>
                        {b.error ? (
                          <span className={styles.errText}>Access error</span>
                        ) : b.file_types?.length === 0 ? (
                          <span className={styles.empty2}>Empty</span>
                        ) : (
                          <div className={styles.pillRow}>
                            {b.file_types?.slice(0, 4).map(f => (
                              <span key={f.ext} className={styles.extSmall}
                                    style={{ "--ext-color": EXT_COLORS[f.ext] || "#6b7280" } as any}>
                                .{f.ext} <em>{f.count}</em>
                              </span>
                            ))}
                            {(b.file_types?.length ?? 0) > 4 && (
                              <span className={styles.more}>+{(b.file_types?.length ?? 0) - 4} more</span>
                            )}
                          </div>
                        )}
                      </td>
                      <td>
                        {b.lambda_triggers?.length === 0 ? (
                          <span className={styles.none}>None</span>
                        ) : (
                          <div className={styles.pillRow}>
                            {b.lambda_triggers?.map(l => (
                              <span key={l.arn} className={styles.lambdaPill}>
                                <Zap size={10} /> {l.function}
                              </span>
                            ))}
                          </div>
                        )}
                      </td>
                      <td>
                        <span className={b.versioning ? styles.verOn : styles.verOff}>
                          {b.versioning ? "ON" : "OFF"}
                        </span>
                      </td>
                    </tr>

                    {/* Expanded detail row */}
                    {isOpen && (
                      <tr key={`${b.name}-detail`} className={styles.detailRow}>
                        <td />
                        <td colSpan={7}>
                          <div className={styles.detailGrid}>

                            {/* File types detail */}
                            <div className={styles.detailBox}>
                              <h4><FileText size={13} /> File Types</h4>
                              {b.file_types?.length === 0 ? (
                                <p className={styles.empty2}>No objects found (bucket is empty or no access).</p>
                              ) : (
                                <table className={styles.miniTable}>
                                  <thead>
                                    <tr><th>Extension</th><th>Count</th><th>Share</th></tr>
                                  </thead>
                                  <tbody>
                                    {b.file_types?.map(f => {
                                      const pct = b.object_count > 0
                                        ? Math.round((f.count / b.object_count) * 100) : 0;
                                      return (
                                        <tr key={f.ext}>
                                          <td>
                                            <span className={styles.extSmall}
                                                  style={{ "--ext-color": EXT_COLORS[f.ext] || "#6b7280" } as any}>
                                              .{f.ext}
                                            </span>
                                          </td>
                                          <td>{f.count}</td>
                                          <td>
                                            <div className={styles.bar}>
                                              <div className={styles.barFill}
                                                   style={{ width: `${pct}%`,
                                                            background: EXT_COLORS[f.ext] || "#6b7280" }} />
                                              <span>{pct}%</span>
                                            </div>
                                          </td>
                                        </tr>
                                      );
                                    })}
                                  </tbody>
                                </table>
                              )}
                            </div>

                            {/* Lambda detail */}
                            <div className={styles.detailBox}>
                              <h4><Zap size={13} /> Lambda Triggers</h4>
                              {b.lambda_triggers?.length === 0 ? (
                                <p className={styles.empty2}>No Lambda functions connected to this bucket.</p>
                              ) : (
                                <table className={styles.miniTable}>
                                  <thead>
                                    <tr><th>Function</th><th>Events</th></tr>
                                  </thead>
                                  <tbody>
                                    {b.lambda_triggers?.map(l => (
                                      <tr key={l.arn}>
                                        <td><span className={styles.lambdaPill}><Zap size={10}/> {l.function}</span></td>
                                        <td className={styles.eventsCell}>
                                          {l.events.map(e => (
                                            <span key={e} className={styles.eventTag}>{e.replace("s3:", "")}</span>
                                          ))}
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              )}
                            </div>

                          </div>

                          {b.error && (
                            <div className={styles.errBox}>Error: {b.error}</div>
                          )}
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
