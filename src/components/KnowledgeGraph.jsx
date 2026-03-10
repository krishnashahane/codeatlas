import React, { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import {
  COLORS,
  addZoom,
  createTooltip,
  showTooltip,
  hideTooltip,
  addDrag,
  createLegend,
} from "../utils/graphHelpers";

const styles = {
  searchBar: {
    position: "absolute",
    top: "12px",
    right: "20px",
    zIndex: 10,
    display: "flex",
    gap: "8px",
  },
  searchInput: {
    padding: "8px 14px",
    background: "#1e293b",
    border: "1px solid #334155",
    borderRadius: "8px",
    color: "#f1f5f9",
    fontSize: "13px",
    outline: "none",
    width: "220px",
  },
};

export default function KnowledgeGraph({ graph }) {
  const containerRef = useRef(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    if (!containerRef.current || !graph.nodes.length) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight || 600;

    d3.select(container).selectAll("svg").remove();

    const svg = d3
      .select(container)
      .append("svg")
      .attr("width", width)
      .attr("height", height)
      .style("background", "#0a0e17");

    const g = svg.append("g");
    addZoom(svg, g);

    const tooltip = createTooltip();

    // Filter nodes if search is active
    const lowerFilter = filter.toLowerCase();
    let filteredNodes = graph.nodes;
    let filteredEdges = graph.edges;

    if (lowerFilter) {
      const matchIds = new Set(
        graph.nodes
          .filter(
            (n) =>
              n.label.toLowerCase().includes(lowerFilter) ||
              n.id.toLowerCase().includes(lowerFilter)
          )
          .map((n) => n.id)
      );

      // Include connected nodes
      graph.edges.forEach((e) => {
        if (matchIds.has(e.source) || matchIds.has(e.source?.id)) {
          matchIds.add(typeof e.target === "string" ? e.target : e.target.id);
        }
        if (matchIds.has(e.target) || matchIds.has(e.target?.id)) {
          matchIds.add(typeof e.source === "string" ? e.source : e.source.id);
        }
      });

      filteredNodes = graph.nodes.filter((n) => matchIds.has(n.id));
      filteredEdges = graph.edges.filter((e) => {
        const src = typeof e.source === "string" ? e.source : e.source.id;
        const tgt = typeof e.target === "string" ? e.target : e.target.id;
        return matchIds.has(src) && matchIds.has(tgt);
      });
    }

    const nodes = filteredNodes.map((n) => ({ ...n, metadata: { ...n.metadata } }));
    const edges = filteredEdges.map((e) => ({ ...e }));

    const simulation = d3
      .forceSimulation(nodes)
      .force(
        "link",
        d3
          .forceLink(edges)
          .id((d) => d.id)
          .distance(60)
      )
      .force("charge", d3.forceManyBody().strength(-120))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(20));

    // Edge styles by type
    const edgeStyles = {
      defines: { dash: "none", color: "#334155" },
      inherits: { dash: "8,4", color: "#a78bfa" },
      calls: { dash: "4,2", color: "#22d3ee" },
      imports: { dash: "none", color: "#475569" },
    };

    // Draw edges
    const link = g
      .append("g")
      .selectAll("line")
      .data(edges)
      .join("line")
      .attr("stroke", (d) => edgeStyles[d.type]?.color || "#475569")
      .attr("stroke-opacity", 0.4)
      .attr("stroke-width", 1.2)
      .attr("stroke-dasharray", (d) => edgeStyles[d.type]?.dash || "none");

    // Draw nodes
    const node = g
      .append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .call(addDrag(simulation));

    node
      .append("circle")
      .attr("r", (d) => {
        if (d.type === "class") return 12;
        if (d.type === "function") return 8;
        if (d.type === "file") return 6;
        return 5;
      })
      .attr("fill", (d) => COLORS[d.type] || COLORS.file)
      .attr("fill-opacity", 0.8)
      .attr("stroke", (d) => COLORS[d.type] || COLORS.file)
      .attr("stroke-width", 1.5)
      .attr("stroke-opacity", 0.5);

    // Labels (only for classes and functions, skip files and variables to reduce clutter)
    node
      .filter((d) => d.type === "class" || d.type === "function")
      .append("text")
      .text((d) => d.label)
      .attr("dy", (d) => (d.type === "class" ? 22 : 18))
      .attr("text-anchor", "middle")
      .attr("fill", "#94a3b8")
      .attr("font-size", (d) => (d.type === "class" ? "12px" : "10px"))
      .attr("font-weight", (d) => (d.type === "class" ? "600" : "400"))
      .style("pointer-events", "none");

    // Tooltip
    node
      .on("mouseover", (event, d) => {
        let html = `<b>${d.label}</b><br>Type: ${d.type}`;
        if (d.type === "class") {
          const methods = d.metadata?.methods || [];
          const bases = d.metadata?.bases || [];
          if (bases.length) html += `<br>Extends: ${bases.join(", ")}`;
          if (methods.length)
            html += `<br>Methods: ${methods.slice(0, 8).join(", ")}${methods.length > 8 ? "..." : ""}`;
        } else if (d.type === "function") {
          const params = d.metadata?.params || [];
          if (params.length) html += `<br>Params: ${params.join(", ")}`;
          if (d.metadata?.is_async) html += `<br><b>async</b>`;
        }
        showTooltip(tooltip, event, html);

        // Highlight connections
        link
          .attr("stroke-opacity", (l) => {
            const src = typeof l.source === "object" ? l.source.id : l.source;
            const tgt = typeof l.target === "object" ? l.target.id : l.target;
            return src === d.id || tgt === d.id ? 0.9 : 0.1;
          });
      })
      .on("mousemove", (event) => {
        tooltip
          .style("left", event.clientX + 12 + "px")
          .style("top", event.clientY - 10 + "px");
      })
      .on("mouseout", () => {
        hideTooltip(tooltip);
        link.attr("stroke-opacity", 0.4);
      });

    simulation.on("tick", () => {
      link
        .attr("x1", (d) => d.source.x)
        .attr("y1", (d) => d.source.y)
        .attr("x2", (d) => d.target.x)
        .attr("y2", (d) => d.target.y);

      node.attr("transform", (d) => `translate(${d.x},${d.y})`);
    });

    // Legend
    createLegend(
      svg,
      [
        { label: "Class", color: COLORS.class },
        { label: "Function", color: COLORS.function },
        { label: "Variable", color: COLORS.variable },
        { label: "File", color: COLORS.file },
      ],
      { x: 20, y: 20 }
    );

    return () => {
      simulation.stop();
      tooltip.remove();
    };
  }, [graph, filter]);

  if (!graph.nodes.length) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          color: "#64748b",
        }}
      >
        No code symbols detected
      </div>
    );
  }

  return (
    <div style={{ position: "relative", width: "100%", height: "100%", minHeight: "600px" }}>
      <div style={styles.searchBar}>
        <input
          style={styles.searchInput}
          type="text"
          placeholder="Search symbols..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>
      <div ref={containerRef} style={{ width: "100%", height: "100%", minHeight: "600px" }} />
    </div>
  );
}
