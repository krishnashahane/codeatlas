import React, { useState } from "react";
import UploadForm from "./components/UploadForm";
import Dashboard from "./components/Dashboard";
import { getAnalysis } from "./api";

const styles = {
  app: {
    minHeight: "100vh",
    display: "flex",
    flexDirection: "column",
  },
  header: {
    padding: "20px 32px",
    borderBottom: "1px solid #1e293b",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    background: "linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)",
  },
  logo: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
  },
  title: {
    fontSize: "24px",
    fontWeight: "700",
    background: "linear-gradient(135deg, #60a5fa, #a78bfa, #f472b6)",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
  },
  subtitle: {
    fontSize: "13px",
    color: "#64748b",
  },
  resetBtn: {
    padding: "8px 16px",
    background: "#1e293b",
    border: "1px solid #334155",
    borderRadius: "8px",
    color: "#94a3b8",
    cursor: "pointer",
    fontSize: "13px",
  },
  main: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
  },
};

export default function App() {
  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleUploadComplete = async (sessionId) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAnalysis(sessionId);
      setAnalysisData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setAnalysisData(null);
    setError(null);
  };

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <div style={styles.logo}>
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="14" stroke="url(#grad)" strokeWidth="2" />
            <circle cx="16" cy="10" r="3" fill="#60a5fa" />
            <circle cx="10" cy="20" r="3" fill="#a78bfa" />
            <circle cx="22" cy="20" r="3" fill="#f472b6" />
            <line x1="16" y1="13" x2="10" y2="17" stroke="#475569" strokeWidth="1.5" />
            <line x1="16" y1="13" x2="22" y2="17" stroke="#475569" strokeWidth="1.5" />
            <line x1="10" y1="20" x2="22" y2="20" stroke="#475569" strokeWidth="1.5" />
            <defs>
              <linearGradient id="grad" x1="0" y1="0" x2="32" y2="32">
                <stop offset="0%" stopColor="#60a5fa" />
                <stop offset="100%" stopColor="#f472b6" />
              </linearGradient>
            </defs>
          </svg>
          <div>
            <div style={styles.title}>CodeAtlas</div>
            <div style={styles.subtitle}>AI Codebase Brain</div>
          </div>
        </div>
        {analysisData && (
          <button style={styles.resetBtn} onClick={handleReset}>
            Analyze Another Repo
          </button>
        )}
      </header>

      <main style={styles.main}>
        {!analysisData ? (
          <UploadForm
            onUploadComplete={handleUploadComplete}
            loading={loading}
            error={error}
          />
        ) : (
          <Dashboard data={analysisData} />
        )}
      </main>
    </div>
  );
}
