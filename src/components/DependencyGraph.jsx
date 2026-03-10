import React, { useEffect, useRef } from "react";
import * as d3 from "d3";
import {
  COLORS,
  createForceSimulation,
  addZoom,
  createTooltip,
  showTooltip,
  hideTooltip,
  addDrag,
  createLegend,
} from "../utils/graphHelpers";

export default function DependencyGraph({ graph }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !graph.nodes.length) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight || 600;

    d3.select(container).selectAll("*").remove();

    const svg = d3
      .select(container)
      .append("svg")
      .attr("width", width)
      .attr("height", height)
      .style("background", "#0a0e17");

    const g = svg.append("g");
    addZoom(svg, g);

    const tooltip = createTooltip();

    const nodes = graph.nodes.map((n) => ({ ...n, metadata: { ...n.metadata } }));
    const edges = graph.edges.map((e) => ({ ...e }));

    // Count connections per node for sizing
    const connectionCount = {};
    edges.forEach((e) => {
      connectionCount[e.source] = (connectionCount[e.source] || 0) + 1;
      connectionCount[e.target] = (connectionCount[e.target] || 0) + 1;
    });

    const simulation = d3
      .forceSimulation(nodes)
      .force(
        "link",
        d3
          .forceLink(edges)
          .id((d) => d.id)
          .distance(100)
      )
      .force("charge", d3.forceManyBody().strength(-150))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(25));

    // Arrow marker
    svg
      .append("defs")
      .append("marker")
      .attr("id", "dep-arrow")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 18)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#475569");

    // Draw edges
    const link = g
      .append("g")
      .selectAll("line")
      .data(edges)
      .join("line")
      .attr("stroke", COLORS.imports)
      .attr("stroke-opacity", 0.4)
      .attr("stroke-width", (d) => Math.min(d.weight || 1, 5))
      .attr("marker-end", "url(#dep-arrow)");

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
        const conns = connectionCount[d.id] || 1;
        return d.type === "package" ? 10 : 5 + Math.min(conns * 1.5, 15);
      })
      .attr("fill", (d) => {
        if (d.type === "package") return COLORS.package;
        if (d.metadata?.is_entry_point) return "#fbbf24";
        return COLORS[d.metadata?.layer] || COLORS.file;
      })
      .attr("fill-opacity", 0.8)
      .attr("stroke", (d) => {
        if (d.type === "package") return COLORS.package;
        return "rgba(255,255,255,0.1)";
      })
      .attr("stroke-width", 1.5);

    // Labels
    node
      .append("text")
      .text((d) => d.label)
      .attr("dy", (d) => {
        const conns = connectionCount[d.id] || 1;
        return (d.type === "package" ? 10 : 5 + Math.min(conns * 1.5, 15)) + 14;
      })
      .attr("text-anchor", "middle")
      .attr("fill", "#94a3b8")
      .attr("font-size", "10px")
      .style("pointer-events", "none");

    // Tooltip
    node
      .on("mouseover", (event, d) => {
        const conns = connectionCount[d.id] || 0;
        const info =
          d.type === "package"
            ? `<b>${d.label}</b><br>External Package`
            : `<b>${d.label}</b><br>Module: ${d.metadata?.module || ""}<br>Connections: ${conns}${d.metadata?.is_entry_point ? "<br><b>Entry Point</b>" : ""}`;
        showTooltip(tooltip, event, info);

        // Highlight connected edges
        link
          .attr("stroke-opacity", (l) =>
            l.source.id === d.id || l.target.id === d.id ? 0.9 : 0.1
          )
          .attr("stroke", (l) =>
            l.source.id === d.id || l.target.id === d.id ? "#60a5fa" : COLORS.imports
          );
      })
      .on("mousemove", (event) => {
        tooltip
          .style("left", event.clientX + 12 + "px")
          .style("top", event.clientY - 10 + "px");
      })
      .on("mouseout", () => {
        hideTooltip(tooltip);
        link
          .attr("stroke-opacity", 0.4)
          .attr("stroke", COLORS.imports);
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
        { label: "Source File", color: COLORS.file },
        { label: "External Package", color: COLORS.package },
        { label: "Entry Point", color: "#fbbf24" },
      ],
      { x: 20, y: 20 }
    );

    return () => {
      simulation.stop();
      tooltip.remove();
    };
  }, [graph]);

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
        No dependencies detected
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100%", minHeight: "600px" }}
    />
  );
}
