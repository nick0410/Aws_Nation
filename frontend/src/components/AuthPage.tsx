import { useState } from "react";
import { Cloud, User, Lock, Key, Globe } from "lucide-react";
import { useAuth } from "../AuthContext";
import styles from "./AuthPage.module.css";

const AWS_REGIONS = [
  "ap-south-1",
  "us-east-1",
  "us-east-2",
  "us-west-1",
  "us-west-2",
  "eu-west-1",
  "eu-west-2",
  "eu-central-1",
  "ap-southeast-1",
  "ap-southeast-2",
  "ap-northeast-1",
  "sa-east-1",
];

export default function AuthPage() {
  const { login, signup } = useAuth();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Form fields
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [awsAccessKey, setAwsAccessKey] = useState("");
  const [awsSecretKey, setAwsSecretKey] = useState("");
  const [awsRegion, setAwsRegion] = useState("ap-south-1");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (mode === "login") {
        await login(username, password);
      } else {
        await signup(username, password, awsAccessKey, awsSecretKey, awsRegion);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const switchMode = (m: "login" | "signup") => {
    setMode(m);
    setError("");
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        {/* Logo */}
        <div className={styles.logoRow}>
          <div className={styles.logoIcon}>
            <Cloud size={22} />
          </div>
          <h1 className={styles.title}>AWS AutoNation</h1>
        </div>
        <p className={styles.subtitle}>
          {mode === "login"
            ? "Sign in to manage your S3 buckets"
            : "Create an account with your AWS credentials"}
        </p>

        {/* Tabs */}
        <div className={styles.tabs}>
          <button
            className={`${styles.tab} ${mode === "login" ? styles.tabActive : ""}`}
            onClick={() => switchMode("login")}
          >
            Login
          </button>
          <button
            className={`${styles.tab} ${mode === "signup" ? styles.tabActive : ""}`}
            onClick={() => switchMode("signup")}
          >
            Sign Up
          </button>
        </div>

        {error && <div className={styles.error}>{error}</div>}

        <form className={styles.form} onSubmit={handleSubmit}>
          {/* Username */}
          <div className="form-group">
            <label>
              <User size={12} style={{ marginRight: 4, verticalAlign: "middle" }} />
              Username
            </label>
            <input
              type="text"
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              minLength={3}
              autoComplete="username"
            />
          </div>

          {/* Password */}
          <div className="form-group">
            <label>
              <Lock size={12} style={{ marginRight: 4, verticalAlign: "middle" }} />
              Password
            </label>
            <input
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={4}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
            />
          </div>

          {/* AWS Credentials — only on signup */}
          {mode === "signup" && (
            <>
              <div className={styles.dividerLabel}>AWS Credentials</div>

              <div className="form-group">
                <label>
                  <Key size={12} style={{ marginRight: 4, verticalAlign: "middle" }} />
                  Access Key ID
                </label>
                <input
                  type="text"
                  placeholder="AKIA..."
                  value={awsAccessKey}
                  onChange={(e) => setAwsAccessKey(e.target.value)}
                  required
                  autoComplete="off"
                />
                <span className={styles.hint}>
                  Found in AWS Console → IAM → Security credentials
                </span>
              </div>

              <div className="form-group">
                <label>
                  <Key size={12} style={{ marginRight: 4, verticalAlign: "middle" }} />
                  Secret Access Key
                </label>
                <input
                  type="password"
                  placeholder="Your secret key"
                  value={awsSecretKey}
                  onChange={(e) => setAwsSecretKey(e.target.value)}
                  required
                  autoComplete="off"
                />
              </div>

              <div className="form-group">
                <label>
                  <Globe size={12} style={{ marginRight: 4, verticalAlign: "middle" }} />
                  Default AWS Region
                </label>
                <select
                  value={awsRegion}
                  onChange={(e) => setAwsRegion(e.target.value)}
                >
                  {AWS_REGIONS.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </div>
            </>
          )}

          <button
            type="submit"
            className={styles.submitBtn}
            disabled={loading}
          >
            {loading
              ? "Please wait..."
              : mode === "login"
                ? "Sign In"
                : "Create Account"}
          </button>
        </form>
      </div>
    </div>
  );
}
