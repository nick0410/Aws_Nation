import { useState, useEffect } from "react";
import { DollarSign, TrendingDown, Zap, RefreshCw, Info, CheckCircle } from "lucide-react";
import toast from "react-hot-toast";
import { listBuckets, estimateCost } from "../api";
import styles from "./CostPredictor.module.css";

interface ClassResult {
  class:            string;
  color:            string;
  description:      string;
  storage_cost:     number;
  put_cost:         number;
  get_cost:         number;
  transfer_cost:    number;
  retrieval_cost:   number;
  monitoring_cost:  number;
  total:            number;
  annual:           number;
}

interface CostResult {
  breakdown:              Record<string, ClassResult>;
  recommended_class:      string;
  recommended_label:      string;
  standard_monthly:       number;
  recommended_monthly:    number;
  savings_vs_standard:    number;
  access_pattern:         string;
  tip:                    string;
  inputs: {
    storage_gb:             number;
    effective_storage_gb:   number;
    put_requests_per_day:   number;
    get_requests_per_day:   number;
    transfer_out_gb_month:  number;
    versioning_enabled:     boolean;
    object_count:           number;
  };
}



export default function CostPredictor() {
  const [buckets, setBuckets]         = useState<{ name: string }[]>([]);
  const [selectedBucket, setSelected] = useState("");
  const [storageGb, setStorageGb]     = useState(10);
  const [putReqs, setPutReqs]         = useState(100);
  const [getReqs, setGetReqs]         = useState(500);
  const [transfer, setTransfer]       = useState(1);
  const [versioning, setVersioning]   = useState(false);
  const [loading, setLoading]         = useState(false);
  const [result, setResult]           = useState<CostResult | null>(null);
  const [activeClass, setActiveClass] = useState<string | null>(null);

  useEffect(() => {
    listBuckets().then(({ data }) => setBuckets(data.buckets ?? [])).catch(() => {});
  }, []);

  const handleBucketChange = (name: string) => {
    setSelected(name);
    setResult(null);
  };

  const handleEstimate = async () => {
    if (storageGb <= 0) { toast.error("Storage must be > 0 GB"); return; }
    setLoading(true);
    setResult(null);
    try {
      const { data } = await estimateCost({
        bucket_name:           selectedBucket || undefined,
        storage_gb:            storageGb,
        put_requests_per_day:  putReqs,
        get_requests_per_day:  getReqs,
        transfer_out_gb_month: transfer,
        versioning_enabled:    versioning,
      });
      setResult(data);
      setActiveClass(data.recommended_class);
      toast.success("Cost estimate ready!");
    } catch {
      toast.error("Estimation failed. Check backend.");
    } finally {
      setLoading(false);
    }
  };

  const fmtUsd = (v: number) => v < 0.01 ? "<$0.01" : `$${v.toFixed(3)}`;

  return (
    <div className={styles.wrap}>

      {/* Header */}
      <div className={styles.pageHeader}>
        <div className={styles.pageIcon}><DollarSign size={28} /></div>
        <div>
          <h1 className={styles.pageTitle}>S3 Cost Predictor</h1>
          <p className={styles.pageSub}>Predict monthly AWS S3 costs across all storage classes — powered by real ap-south-1 pricing</p>
        </div>
      </div>

      {/* Input Card */}
      <div className="card">
        <div className={styles.sectionHead}>
          <Zap size={18} color="var(--primary)" />
          <h2>Configure Your Workload</h2>
        </div>

        <div className={styles.grid}>
          {/* Bucket selector */}
          <div className={styles.field}>
            <label>Bucket</label>
            <select value={selectedBucket} onChange={e => handleBucketChange(e.target.value)} className={styles.select}>
              <option value="">— Manual input (no bucket) —</option>
              {buckets.map(b => <option key={b.name} value={b.name}>{b.name}</option>)}
            </select>
            {selectedBucket && (
              <span className={styles.hint}>
                <Info size={11} /> Versioning status will be auto-fetched from AWS
              </span>
            )}
          </div>

          {/* Storage */}
          <div className={styles.field}>
            <label>Expected Storage <span className={styles.unit}>GB/month</span></label>
            <input type="number" min="0.1" step="0.1" value={storageGb}
              onChange={e => setStorageGb(parseFloat(e.target.value) || 0)}
              className={styles.input} />
          </div>

          {/* PUT requests */}
          <div className={styles.field}>
            <label>PUT / Write Requests <span className={styles.unit}>per day</span></label>
            <input type="number" min="0" value={putReqs}
              onChange={e => setPutReqs(parseInt(e.target.value) || 0)}
              className={styles.input} />
          </div>

          {/* GET requests */}
          <div className={styles.field}>
            <label>GET / Read Requests <span className={styles.unit}>per day</span></label>
            <input type="number" min="0" value={getReqs}
              onChange={e => setGetReqs(parseInt(e.target.value) || 0)}
              className={styles.input} />
          </div>

          {/* Data transfer */}
          <div className={styles.field}>
            <label>Data Transfer Out <span className={styles.unit}>GB/month</span></label>
            <input type="number" min="0" step="0.1" value={transfer}
              onChange={e => setTransfer(parseFloat(e.target.value) || 0)}
              className={styles.input} />
          </div>

          {/* Versioning toggle (only if no bucket selected) */}
          {!selectedBucket && (
            <div className={styles.field}>
              <label>Versioning</label>
              <div className={styles.toggleRow}>
                <label className={styles.toggle}>
                  <input type="checkbox" checked={versioning} onChange={e => setVersioning(e.target.checked)} />
                  <span className={styles.slider} />
                </label>
                <span style={{ fontSize: 13, color: versioning ? "var(--success)" : "var(--text-muted)" }}>
                  {versioning ? "Enabled (+50% storage estimate)" : "Disabled"}
                </span>
              </div>
            </div>
          )}
        </div>

        <button className={`btn btn-primary ${styles.estimateBtn}`} onClick={handleEstimate} disabled={loading}>
          {loading
            ? <><RefreshCw size={16} className={styles.spin} /> Analysing…</>
            : <><DollarSign size={16} /> Estimate Cost</>
          }
        </button>
      </div>

      {/* Results */}
      {result && (
        <>
          {/* Savings banner */}
          {result.savings_vs_standard > 0 && (
            <div className={styles.savingsBanner}>
              <TrendingDown size={20} />
              <span>
                Switch to <strong>{result.recommended_label}</strong> and save&nbsp;
                <strong>{result.savings_vs_standard}%</strong>&nbsp;
                (~<strong>${(result.standard_monthly - result.recommended_monthly).toFixed(3)}/mo</strong> vs Standard)
              </span>
            </div>
          )}

          {/* Tip */}
          <div className={styles.tipBox}>
            <Info size={14} />
            <span>{result.tip}</span>
          </div>

          {/* Class cards */}
          <div className={styles.cardsGrid}>
            {Object.entries(result.breakdown).map(([key, cls]) => {
              const isRec = key === result.recommended_class;
              const isActive = activeClass === key;
              return (
                <div
                  key={key}
                  className={`${styles.classCard} ${isRec ? styles.recommended : ""} ${isActive ? styles.active : ""}`}
                  onClick={() => setActiveClass(key)}
                  style={{ "--card-color": cls.color } as any}
                >
                  {isRec && <div className={styles.recBadge}><CheckCircle size={12} /> Recommended</div>}
                  <div className={styles.cardLabel}>{cls.class}</div>
                  <div className={styles.cardDesc}>{cls.description}</div>
                  <div className={styles.cardPrice}>{fmtUsd(cls.total)}<span>/mo</span></div>
                  <div className={styles.cardAnnual}>{fmtUsd(cls.annual)} / year</div>
                </div>
              );
            })}
          </div>

          {/* Breakdown table for active class */}
          {activeClass && result.breakdown[activeClass] && (
            <div className="card" style={{ marginTop: 0 }}>
              <div className={styles.sectionHead}>
                <h2>{result.breakdown[activeClass].class} — Cost Breakdown</h2>
              </div>

              <table className={styles.breakdownTable}>
                <thead>
                  <tr><th>Component</th><th>Details</th><th>Monthly Cost</th></tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Storage</td>
                    <td>{result.inputs.effective_storage_gb} GB × pricing</td>
                    <td>{fmtUsd(result.breakdown[activeClass].storage_cost)}</td>
                  </tr>
                  <tr>
                    <td>PUT Requests</td>
                    <td>{(result.inputs.put_requests_per_day * 30).toLocaleString()} reqs/month</td>
                    <td>{fmtUsd(result.breakdown[activeClass].put_cost)}</td>
                  </tr>
                  <tr>
                    <td>GET Requests</td>
                    <td>{(result.inputs.get_requests_per_day * 30).toLocaleString()} reqs/month</td>
                    <td>{fmtUsd(result.breakdown[activeClass].get_cost)}</td>
                  </tr>
                  <tr>
                    <td>Data Transfer Out</td>
                    <td>{result.inputs.transfer_out_gb_month} GB/month</td>
                    <td>{fmtUsd(result.breakdown[activeClass].transfer_cost)}</td>
                  </tr>
                  {result.breakdown[activeClass].retrieval_cost > 0 && (
                    <tr>
                      <td>Retrieval</td>
                      <td>Per-GB retrieval fee</td>
                      <td>{fmtUsd(result.breakdown[activeClass].retrieval_cost)}</td>
                    </tr>
                  )}
                  {result.breakdown[activeClass].monitoring_cost > 0 && (
                    <tr>
                      <td>Monitoring</td>
                      <td>{result.inputs.object_count.toLocaleString()} objects</td>
                      <td>{fmtUsd(result.breakdown[activeClass].monitoring_cost)}</td>
                    </tr>
                  )}
                  <tr className={styles.totalRow}>
                    <td colSpan={2}><strong>Total Monthly</strong></td>
                    <td><strong>{fmtUsd(result.breakdown[activeClass].total)}</strong></td>
                  </tr>
                  <tr className={styles.annualRow}>
                    <td colSpan={2}>Total Annual (×12)</td>
                    <td>{fmtUsd(result.breakdown[activeClass].annual)}</td>
                  </tr>
                </tbody>
              </table>

              <div className={styles.disclaimer}>
                * Prices based on AWS ap-south-1 (Mumbai) as of 2026. Actual costs may vary.
                {result.inputs.versioning_enabled && " Versioning ON: storage estimate ×1.5."}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
