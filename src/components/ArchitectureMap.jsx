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
  nodeRadius,
} from "../utils/graphHelpers";

export default function ArchitectureMap({ graph }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !graph.nodes.length) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight || 600;

    // Clear previous
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

    // Deep clone data for D3 mutation
    const nodes = graph.nodes.map((n) => ({ ...n, metadata: { ...n.metadata } }));
    const edges = graph.edges.map((e) => ({ ...e }));

    const simulation = createForceSimulation(nodes, edges, { width, height });

    // Draw edges
    const link = g
      .append("g")
      .selectAll("line")
      .data(edges)
      .join("line")
      .attr("stroke", COLORS.depends_on)
      .attr("stroke-opacity", 0.5)
      .attr("stroke-width", 1.5)
      .attr("marker-end", "url(#arrow)");

    // Arrow marker
    svg
      .append("defs")
      .append("marker")
      .attr("id", "arrow")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 20)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#475569");

    // Draw nodes
    const node = g
      .append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .call(addDrag(simulation));

    // Node shape: diamond for entry points, circle for others
    node.each(function (d) {
      const el = d3.select(this);
      const color = COLORS[d.metadata?.layer] || COLORS.Core;
      const r = nodeRadius(d);

      if (d.metadata?.has_entry_point) {
        el.append("polygon")
          .attr("points", `0,${-r} ${r},0 0,${r} ${-r},0`)
          .attr("fill", color)
          .attr("fill-opacity", 0.8)
          .attr("stroke", color)
          .attr("stroke-width", 2);
      } else {
        el.append("circle")
          .attr("r", r)
          .attr("fill", color)
          .attr("fill-opacity", 0.7)
          .attr("stroke", color)
          .attr("stroke-width", 1.5);
      }
    });

    // Labels
    node
      .append("text")
      .text((d) => d.label)
      .attr("dy", (d) => nodeRadius(d) + 14)
      .attr("text-anchor", "middle")
      .attr("fill", "#94a3b8")
      .attr("font-size", "11px")
      .style("pointer-events", "none");

    // Tooltip
    node
      .on("mouseover", (event, d) => {
        const layer = d.metadata?.layer || "Core";
        const files = d.metadata?.file_count || 0;
        const entry = d.metadata?.has_entry_point ? "<br><b>Entry Point</b>" : "";
        showTooltip(
          tooltip,
          event,
          `<b>${d.label}</b><br>Layer: ${layer}<br>Files: ${files}${entry}`
        );
      })
      .on("mousemove", (event) => {
        tooltip
          .style("left", event.clientX + 12 + "px")
          .style("top", event.clientY - 10 + "px");
      })
      .on("mouseout", () => hideTooltip(tooltip));

    // Simulation tick
    simulation.on("tick", () => {
      link
        .attr("x1", (d) => d.source.x)
        .attr("y1", (d) => d.source.y)
        .attr("x2", (d) => d.target.x)
        .attr("y2", (d) => d.target.y);

      node.attr("transform", (d) => `translate(${d.x},${d.y})`);
    });

    // Legend
    const layers = [...new Set(nodes.map((n) => n.metadata?.layer).filter(Boolean))];
    createLegend(
      svg,
      layers.map((l) => ({ label: l, color: COLORS[l] || COLORS.Core })),
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
        No module structure detected
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
