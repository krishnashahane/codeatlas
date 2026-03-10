import React, { useState } from "react";
import ArchitectureMap from "./ArchitectureMap";
import DependencyGraph from "./DependencyGraph";
import KnowledgeGraph from "./KnowledgeGraph";

const styles = {
  container: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
  },
  statsBar: {
    display: "flex",
    gap: "24px",
    padding: "16px 32px",
    background: "#111827",
    borderBottom: "1px solid #1e293b",
    overflowX: "auto",
  },
  stat: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    minWidth: "80px",
  },
  statValue: {
    fontSize: "22px",
    fontWeight: "700",
    color: "#f1f5f9",
  },
  statLabel: {
    fontSize: "11px",
    color: "#64748b",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
    marginTop: "2px",
  },
  tabs: {
    display: "flex",
    gap: "0",
    padding: "12px 32px",
    background: "#0f172a",
    borderBottom: "1px solid #1e293b",
  },
  tab: (active) => ({
    padding: "10px 24px",
    background: active
      ? "linear-gradient(135deg, rgba(59,130,246,0.15), rgba(139,92,246,0.15))"
      : "transparent",
    border: active ? "1px solid rgba(99,102,241,0.3)" : "1px solid transparent",
    borderRadius: "8px",
    color: active ? "#f1f5f9" : "#64748b",
    cursor: "pointer",
    fontSize: "14px",
    fontWeight: active ? "600" : "400",
    transition: "all 0.2s",
    marginRight: "8px",
  }),
  graphContainer: {
    flex: 1,
    position: "relative",
    overflow: "hidden",
  },
  languages: {
    display: "flex",
    gap: "8px",
    alignItems: "center",
  },
  langBadge: {
    padding: "4px 10px",
    background: "#1e293b",
    borderRadius: "12px",
    fontSize: "12px",
    color: "#94a3b8",
  },
};

const TABS = [
  { id: "architecture", label: "Architecture Map" },
  { id: "dependencies", label: "Dependency Graph" },
  { id: "knowledge", label: "Knowledge Graph" },
];

export default function Dashboard({ data }) {
  const [activeTab, setActiveTab] = useState("architecture");
  const { summary } = data;

  return (
    <div style={styles.container}>
      <div style={styles.statsBar}>
        <div style={styles.stat}>
          <div style={styles.statValue}>{summary.file_count}</div>
          <div style={styles.statLabel}>Files</div>
        </div>
        <div style={styles.stat}>
          <div style={styles.statValue}>{summary.class_count}</div>
          <div style={styles.statLabel}>Classes</div>
        </div>
        <div style={styles.stat}>
          <div style={styles.statValue}>{summary.function_count}</div>
          <div style={styles.statLabel}>Functions</div>
        </div>
        <div style={styles.stat}>
          <div style={styles.statValue}>{summary.variable_count}</div>
          <div style={styles.statLabel}>Variables</div>
        </div>
        <div style={styles.stat}>
          <div style={styles.statValue}>{summary.import_count}</div>
          <div style={styles.statLabel}>Imports</div>
        </div>
        <div style={styles.languages}>
          {(summary.languages || []).map((lang) => (
            <span key={lang} style={styles.langBadge}>
              {lang}
            </span>
          ))}
        </div>
      </div>

      <div style={styles.tabs}>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            style={styles.tab(activeTab === tab.id)}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div style={styles.graphContainer}>
        {activeTab === "architecture" && (
          <ArchitectureMap graph={data.architecture_map} />
        )}
        {activeTab === "dependencies" && (
          <DependencyGraph graph={data.dependency_graph} />
        )}
        {activeTab === "knowledge" && (
          <KnowledgeGraph graph={data.knowledge_graph} />
        )}
      </div>
    </div>
  );
}
