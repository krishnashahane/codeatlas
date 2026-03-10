import React, { useState, useRef } from "react";
import { uploadRepo, uploadGithubUrl } from "../api";

const styles = {
  container: {
    flex: 1,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "40px",
  },
  card: {
    background: "#111827",
    border: "1px solid #1e293b",
    borderRadius: "16px",
    padding: "48px",
    maxWidth: "560px",
    width: "100%",
  },
  heading: {
    fontSize: "28px",
    fontWeight: "700",
    marginBottom: "8px",
    color: "#f1f5f9",
  },
  desc: {
    fontSize: "15px",
    color: "#64748b",
    marginBottom: "32px",
    lineHeight: "1.6",
  },
  tabs: {
    display: "flex",
    gap: "0",
    marginBottom: "24px",
    background: "#0f172a",
    borderRadius: "10px",
    padding: "4px",
  },
  tab: (active) => ({
    flex: 1,
    padding: "10px 16px",
    background: active ? "#1e293b" : "transparent",
    border: "none",
    borderRadius: "8px",
    color: active ? "#f1f5f9" : "#64748b",
    cursor: "pointer",
    fontSize: "14px",
    fontWeight: active ? "600" : "400",
    transition: "all 0.2s",
  }),
  dropZone: (isDragging) => ({
    border: `2px dashed ${isDragging ? "#60a5fa" : "#334155"}`,
    borderRadius: "12px",
    padding: "48px 24px",
    textAlign: "center",
    cursor: "pointer",
    transition: "all 0.2s",
    background: isDragging ? "rgba(96, 165, 250, 0.05)" : "transparent",
  }),
  dropText: {
    fontSize: "15px",
    color: "#94a3b8",
    marginTop: "12px",
  },
  dropHint: {
    fontSize: "13px",
    color: "#475569",
    marginTop: "8px",
  },
  input: {
    width: "100%",
    padding: "14px 16px",
    background: "#0f172a",
    border: "1px solid #334155",
    borderRadius: "10px",
    color: "#f1f5f9",
    fontSize: "15px",
    outline: "none",
  },
  button: (disabled) => ({
    width: "100%",
    padding: "14px",
    background: disabled
      ? "#1e293b"
      : "linear-gradient(135deg, #3b82f6, #8b5cf6)",
    border: "none",
    borderRadius: "10px",
    color: disabled ? "#475569" : "#fff",
    fontSize: "16px",
    fontWeight: "600",
    cursor: disabled ? "not-allowed" : "pointer",
    marginTop: "16px",
    transition: "all 0.2s",
  }),
  error: {
    marginTop: "16px",
    padding: "12px 16px",
    background: "rgba(239, 68, 68, 0.1)",
    border: "1px solid rgba(239, 68, 68, 0.3)",
    borderRadius: "8px",
    color: "#f87171",
    fontSize: "14px",
  },
  fileName: {
    marginTop: "12px",
    fontSize: "14px",
    color: "#60a5fa",
  },
  spinner: {
    display: "inline-block",
    width: "18px",
    height: "18px",
    border: "2px solid rgba(255,255,255,0.3)",
    borderTopColor: "#fff",
    borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
  },
};

export default function UploadForm({ onUploadComplete, loading, error }) {
  const [mode, setMode] = useState("file");
  const [file, setFile] = useState(null);
  const [githubUrl, setGithubUrl] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [localLoading, setLocalLoading] = useState(false);
  const [localError, setLocalError] = useState(null);
  const fileInputRef = useRef(null);

  const isLoading = loading || localLoading;
  const displayError = error || localError;

  const handleFileSelect = (e) => {
    const selected = e.target.files?.[0];
    if (selected) setFile(selected);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) setFile(dropped);
  };

  const handleSubmit = async () => {
    setLocalError(null);
    setLocalLoading(true);

    try {
      let result;
      if (mode === "file" && file) {
        result = await uploadRepo(file);
      } else if (mode === "github" && githubUrl.trim()) {
        result = await uploadGithubUrl(githubUrl.trim());
      } else {
        setLocalError("Please provide a file or GitHub URL");
        setLocalLoading(false);
        return;
      }
      await onUploadComplete(result.session_id);
    } catch (err) {
      setLocalError(err.message);
    } finally {
      setLocalLoading(false);
    }
  };

  const canSubmit =
    !isLoading && ((mode === "file" && file) || (mode === "github" && githubUrl.trim()));

  return (
    <div style={styles.container}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <div style={styles.card}>
        <h1 style={styles.heading}>Analyze Your Codebase</h1>
        <p style={styles.desc}>
          Upload a repository to generate an interactive architecture map,
          dependency graph, and knowledge graph of your code.
        </p>

        <div style={styles.tabs}>
          <button style={styles.tab(mode === "file")} onClick={() => setMode("file")}>
            Upload ZIP
          </button>
          <button style={styles.tab(mode === "github")} onClick={() => setMode("github")}>
            GitHub URL
          </button>
        </div>

        {mode === "file" ? (
          <div>
            <div
              style={styles.dropZone(isDragging)}
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <svg
                width="48"
                height="48"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#475569"
                strokeWidth="1.5"
                style={{ margin: "0 auto", display: "block" }}
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              <div style={styles.dropText}>
                Drag & drop your repo ZIP file here, or click to browse
              </div>
              <div style={styles.dropHint}>Supports .zip files up to 100MB</div>
              {file && <div style={styles.fileName}>{file.name}</div>}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip"
              onChange={handleFileSelect}
              style={{ display: "none" }}
            />
          </div>
        ) : (
          <input
            style={styles.input}
            type="text"
            placeholder="https://github.com/user/repo"
            value={githubUrl}
            onChange={(e) => setGithubUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && canSubmit && handleSubmit()}
          />
        )}

        <button style={styles.button(!canSubmit)} disabled={!canSubmit} onClick={handleSubmit}>
          {isLoading ? <div style={styles.spinner} /> : "Analyze Repository"}
        </button>

        {displayError && <div style={styles.error}>{displayError}</div>}
      </div>
    </div>
  );
}
