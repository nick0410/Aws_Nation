import { useState } from "react";
import { Cpu, Sparkles, RefreshCw, Copy, Check } from "lucide-react";
import toast from "react-hot-toast";
import { summarizeProduct } from "../api";
import styles from "./MLSummary.module.css";

export default function MLSummary() {
  const [productName, setProductName]   = useState("");
  const [description, setDescription]  = useState("");
  const [maxLen, setMaxLen]             = useState(130);
  const [loading, setLoading]           = useState(false);
  const [result, setResult]             = useState<any>(null);
  const [copied, setCopied]             = useState(false);

  const handleSummarize = async () => {
    if (!productName.trim()) return toast.error("Product name is required.");
    if (description.trim().length < 20) return toast.error("Description must be at least 20 characters.");

    setLoading(true);
    setResult(null);
    try {
      const { data } = await summarizeProduct({
        product_name:        productName,
        product_description: description,
        max_length:          maxLen,
        min_length:          30,
      });
      setResult(data);
      toast.success("Summary generated!");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Summarization failed.");
    } finally {
      setLoading(false);
    }
  };

  const copySummary = () => {
    if (!result?.summary) return;
    navigator.clipboard.writeText(result.summary);
    setCopied(true);
    toast.success("Copied to clipboard!");
    setTimeout(() => setCopied(false), 2000);
  };

  const sampleProducts = [
    {
      name: "Sony WH-1000XM5",
      desc: "Sony WH-1000XM5 wireless noise cancelling headphones deliver industry-leading noise cancellation with 8 microphones and two processors. They feature 30-hour battery life with quick charge, LDAC support for high-quality audio, multipoint connection to two devices simultaneously, and an ultra-comfortable over-ear design with 360 Reality Audio. The headphones include Speak-to-Chat technology that automatically pauses music when you start a conversation, Adaptive Sound Control that adjusts ambient sound settings based on your activity, and are foldable for easy portability."
    },
    {
      name: "MacBook Pro M3",
      desc: "The MacBook Pro featuring Apple M3 chip delivers groundbreaking performance with up to 18 hours of battery life. It features a stunning Liquid Retina XDR display with up to 1000 nits of sustained brightness. The M3 chip includes an 8-core CPU and 10-core GPU with hardware-accelerated ray tracing. Available in 14-inch and 16-inch models, it supports up to 24GB of unified memory, Thunderbolt 4 ports, an HDMI port, SD card slot, and MagSafe 3 charging."
    }
  ];

  const loadSample = (s: typeof sampleProducts[0]) => {
    setProductName(s.name);
    setDescription(s.desc);
  };

  return (
    <div className={styles.wrapper}>
      {/* Left – Input */}
      <div className="card">
        <div className={styles.head}>
          <Cpu size={20} color="var(--ml)" />
          <h2>AI Product Summarizer</h2>
          <span className="badge info">HuggingFace BART</span>
        </div>

        <div className={styles.samples}>
          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>Try a sample:</span>
          {sampleProducts.map((s) => (
            <button key={s.name} className="btn btn-outline" style={{ fontSize: 12, padding: "5px 12px" }}
              onClick={() => loadSample(s)}>
              {s.name}
            </button>
          ))}
        </div>

        <div className="form-group">
          <label>Product Name *</label>
          <input
            placeholder="e.g. Sony WH-1000XM5"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label>Product Description *</label>
          <textarea
            placeholder="Paste a long product description here (at least 20 characters)…"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            style={{ minHeight: 160 }}
          />
          <span style={{ fontSize: 11, color: "var(--text-muted)", textAlign: "right" }}>
            {description.split(" ").filter(Boolean).length} words
          </span>
        </div>

        <div className="form-group">
          <label>Max Summary Length: {maxLen} tokens</label>
          <input
            type="range"
            min={50}
            max={250}
            value={maxLen}
            onChange={(e) => setMaxLen(Number(e.target.value))}
            style={{ padding: "4px 0", cursor: "pointer" }}
          />
        </div>

        <button
          className="btn btn-primary"
          style={{ width: "100%", justifyContent: "center", height: 44 }}
          onClick={handleSummarize}
          disabled={loading}
        >
          {loading
            ? <><RefreshCw size={16} className={styles.spin} /> Summarizing…</>
            : <><Sparkles size={16} /> Generate Summary</>}
        </button>
      </div>

      {/* Right – Output */}
      <div className="card">
        <div className={styles.head}>
          <Sparkles size={20} color="var(--primary)" />
          <h2>Generated Summary</h2>
        </div>

        {!result && !loading && (
          <div className={styles.placeholder}>
            <Cpu size={48} color="var(--border)" />
            <p>Fill in the product details and click<br /><strong>Generate Summary</strong> to get an AI-powered summary.</p>
          </div>
        )}

        {loading && (
          <div className={styles.placeholder}>
            <RefreshCw size={40} color="var(--ml)" className={styles.spin} />
            <p style={{ color: "var(--ml)" }}>AI is processing your product description…</p>
            <p style={{ fontSize: 12 }}>This may take a moment on first run (model loading)</p>
          </div>
        )}

        {result && (
          <div className={styles.resultWrap}>
            <div className={styles.statRow}>
              <div className={styles.stat}>
                <span className={styles.statLabel}>Original</span>
                <span className={styles.statVal}>{result.original_length} words</span>
              </div>
              <div className={styles.statArrow}>→</div>
              <div className={styles.stat}>
                <span className={styles.statLabel}>Summary</span>
                <span className={styles.statVal}>
                  {result.summary.split(" ").length} words
                </span>
              </div>
              <div className={styles.stat}>
                <span className={styles.statLabel}>Compression</span>
                <span className={styles.statVal} style={{ color: "var(--success)" }}>
                  {Math.round((1 - result.summary.split(" ").length / result.original_length) * 100)}%
                </span>
              </div>
            </div>

            <div className={styles.summaryBox}>
              <p>{result.summary}</p>
            </div>

            <div className={styles.footer}>
              <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                Model: <code style={{ color: "var(--ml)" }}>{result.model_used}</code>
              </span>
              <button className="btn btn-outline" style={{ padding: "6px 14px", fontSize: 12 }}
                onClick={copySummary}>
                {copied ? <Check size={14} /> : <Copy size={14} />}
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
