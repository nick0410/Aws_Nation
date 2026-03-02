import { Cloud, LayoutList, DollarSign } from "lucide-react";
import styles from "./Header.module.css";

export default function Header({
  activeTab,
  setActiveTab,
}: {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}) {
  const tabs = [
    { id: "s3", label: "S3 Automation", icon: <Cloud size={16} /> },
    { id: "summary", label: "Summary",      icon: <LayoutList size={16} />  },
    { id: "cost", label: "Cost Predictor",   icon: <DollarSign size={16} /> },
  ];

  return (
    <header className={styles.header}>
      <div className={styles.brand}>
        <div className={styles.logo}>
          <Cloud size={22} />
        </div>
        <div>
          <h1 className={styles.title}>AWS AutoNation</h1>
        </div>
      </div>

      <nav className={styles.nav}>
        {tabs.map((t) => (
          <button
            key={t.id}
            className={`${styles.tab} ${activeTab === t.id ? styles.active : ""}`}
            onClick={() => setActiveTab(t.id)}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </nav>


    </header>
  );
}
