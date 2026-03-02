import { useState } from "react";
import { Toaster } from "react-hot-toast";
import { useAuth } from "./AuthContext";
import AuthPage from "./components/AuthPage";
import Header from "./components/Header";
import S3Form from "./components/S3Form";
import BucketSummary from "./components/BucketSummary";
import CostPredictor from "./components/CostPredictor";
import styles from "./App.module.css";

function App() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState("s3");

  if (!user) return <AuthPage />;

  return (
    <div className={styles.app}>
      <Toaster
        position="top-right"
        toastOptions={{
          style: { background: "#1a1d2e", color: "#e8eaf6", border: "1px solid #2e3250" },
          success: { iconTheme: { primary: "#4caf82", secondary: "#1a1d2e" } },
          error:   { iconTheme: { primary: "#f44336", secondary: "#1a1d2e" } },
        }}
      />

      <Header activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className={styles.main}>
        {activeTab === "s3" && <S3Form />}
        {activeTab === "summary" && <BucketSummary />}
        {activeTab === "cost" && <CostPredictor />}
      </main>
    </div>
  );
}

export default App;
