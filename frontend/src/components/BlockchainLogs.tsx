import { useState } from "react";
import { Link, RefreshCw, ExternalLink, Shield, AlertCircle } from "lucide-react";
import toast from "react-hot-toast";
import { getBlockchainLogs, getContractInfo } from "../api";
import styles from "./BlockchainLogs.module.css";

interface BucketLog {
  bucket_name:  string;
  owner_email:  string;
  region:       string;
  timestamp:    string;
  creator_addr: string;
}

interface ContractInfo {
  contract_address:  string;
  network:           string;
  rpc_configured:    boolean;
  key_configured:    boolean;
  connected:         boolean;
  connection_error?: string;
  explorer?:         string;
}

export default function BlockchainLogs() {
  const [logs, setLogs]             = useState<BucketLog[]>([]);
  const [contractInfo, setContractInfo] = useState<ContractInfo | null>(null);
  const [loading, setLoading]       = useState(false);
  const [infoLoading, setInfoLoading] = useState(false);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const { data } = await getBlockchainLogs();
      setLogs(data.logs || []);
      toast.success(`${data.count ?? 0} blockchain log(s) loaded.`);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to fetch logs.");
    } finally {
      setLoading(false);
    }
  };

  const fetchInfo = async () => {
    setInfoLoading(true);
    try {
      const { data } = await getContractInfo();
      setContractInfo(data);
    } catch {
      toast.error("Failed to fetch contract info.");
    } finally {
      setInfoLoading(false);
    }
  };

  return (
    <div className={styles.wrapper}>
      {/* Contract Info Card */}
      <div className={`card ${styles.infoCard}`}>
        <div className={styles.head}>
          <Shield size={20} color="var(--blockchain)" />
          <h2>Smart Contract</h2>
          <button
            className="btn btn-outline"
            style={{ marginLeft: "auto", padding: "6px 14px", fontSize: 12 }}
            onClick={fetchInfo}
            disabled={infoLoading}
          >
            {infoLoading ? <RefreshCw size={12} className={styles.spin} /> : <RefreshCw size={12} />}
            Check
          </button>
        </div>

        <div className={styles.infoGrid}>
          <InfoRow label="Contract"  value={contractInfo?.contract_address || "Not loaded"} />
          <InfoRow label="Network"   value={contractInfo?.network           || "Ethereum Sepolia Testnet"} />
          <InfoRow
            label="RPC Status"
            value={contractInfo ? (contractInfo.rpc_configured ? "Configured" : "Missing") : "—"}
            highlight={contractInfo?.rpc_configured}
          />
          <InfoRow
            label="Wallet Key"
            value={contractInfo ? (contractInfo.key_configured ? "Set" : "Missing") : "—"}
            highlight={contractInfo?.key_configured}
          />
          <InfoRow
            label="Connected"
            value={contractInfo ? (contractInfo.connected ? "Yes" : "No") : "—"}
            highlight={contractInfo?.connected}
          />
        </div>

        {contractInfo?.explorer && (
          <a href={contractInfo.explorer} target="_blank" rel="noreferrer" className={styles.explorerBtn}>
            <ExternalLink size={14} />
            View on Etherscan
          </a>
        )}

        {contractInfo && !contractInfo.connected && (
          <div className={styles.warning}>
            <AlertCircle size={14} />
            <span>Blockchain not connected. Configure <code>.env</code> to enable on-chain logging.</span>
          </div>
        )}

        <div className={styles.solNote}>
          <div className={styles.solHead}>
            <span className="badge purple">Solidity</span>
            <span>BucketLogger.sol</span>
          </div>
          <p>Every S3 bucket creation is logged on-chain with:</p>
          <ul>
            <li>Bucket name</li>
            <li>Owner email</li>
            <li>AWS region</li>
            <li>Block timestamp</li>
            <li>Creator wallet address</li>
          </ul>
        </div>
      </div>

      {/* Logs Card */}
      <div className="card">
        <div className={styles.head}>
          <Link size={20} color="var(--blockchain)" />
          <h2>On-Chain Bucket Logs</h2>
          <button
            className="btn btn-primary"
            style={{ marginLeft: "auto", padding: "8px 16px" }}
            onClick={fetchLogs}
            disabled={loading}
          >
            {loading
              ? <><RefreshCw size={14} className={styles.spin} /> Loading…</>
              : <><RefreshCw size={14} /> Fetch Logs</>}
          </button>
        </div>

        {logs.length === 0 ? (
          <div className={styles.empty}>
            <Link size={40} color="var(--border)" />
            <p>No logs loaded yet.<br />Create an S3 bucket to auto-log it on-chain,<br />then click Fetch Logs.</p>
          </div>
        ) : (
          <div className={styles.logList}>
            {logs.map((log, i) => (
              <div key={i} className={styles.logItem}>
                <div className={styles.logIndex}>#{i + 1}</div>
                <div className={styles.logContent}>
                  <div className={styles.logMain}>
                    <span className={styles.bucketName}>{log.bucket_name}</span>
                    <span className="badge info">{log.region}</span>
                    <span className="badge purple">{log.timestamp}</span>
                  </div>
                  <div className={styles.logSub}>
                    <span>Owner: {log.owner_email}</span>
                    <span>Address: {log.creator_addr.slice(0, 10)}…{log.creator_addr.slice(-6)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function InfoRow({
  label, value, highlight,
}: {
  label: string; value: string; highlight?: boolean;
}) {
  return (
    <div className={styles.infoRow}>
      <span className={styles.infoLabel}>{label}</span>
      <span
        className={styles.infoVal}
        style={{ color: highlight === true ? "var(--success)" : highlight === false ? "var(--error)" : undefined }}
      >
        {value}
      </span>
    </div>
  );
}
