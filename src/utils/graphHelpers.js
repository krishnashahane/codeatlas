import * as d3 from "d3";

export const COLORS = {
  // Node type colors
  file: "#60a5fa",
  directory: "#34d399",
  class: "#a78bfa",
  function: "#22d3ee",
  variable: "#fbbf24",
  package: "#f87171",

  // Layer colors
  API: "#3b82f6",
  "Business Logic": "#10b981",
  Data: "#f59e0b",
  Utility: "#6b7280",
  Config: "#8b5cf6",
  Tests: "#ec4899",
  UI: "#06b6d4",
  Core: "#64748b",

  // Edge type colors
  imports: "#475569",
  depends_on: "#475569",
  defines: "#334155",
  inherits: "#a78bfa",
  calls: "#22d3ee",
};

export function createForceSimulation(nodes, edges, { width, height }) {
  return d3
    .forceSimulation(nodes)
    .force(
      "link",
      d3
        .forceLink(edges)
        .id((d) => d.id)
        .distance(80)
    )
    .force("charge", d3.forceManyBody().strength(-200))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius(30));
}

export function addZoom(svg, g) {
  const zoom = d3
    .zoom()
    .scaleExtent([0.1, 8])
    .on("zoom", (event) => {
      g.attr("transform", event.transform);
    });

  svg.call(zoom);

  // Fit to content after a delay
  setTimeout(() => {
    svg.call(zoom.transform, d3.zoomIdentity);
  }, 100);

  return zoom;
}

export function createTooltip() {
  // Remove existing tooltip
  d3.select(".codeatlas-tooltip").remove();

  return d3
    .select("body")
    .append("div")
    .attr("class", "codeatlas-tooltip")
    .style("position", "fixed")
    .style("pointer-events", "none")
    .style("background", "#1e293b")
    .style("border", "1px solid #334155")
    .style("border-radius", "8px")
    .style("padding", "10px 14px")
    .style("font-size", "13px")
    .style("color", "#e2e8f0")
    .style("box-shadow", "0 8px 32px rgba(0,0,0,0.4)")
    .style("opacity", 0)
    .style("z-index", 9999)
    .style("max-width", "300px");
}

export function showTooltip(tooltip, event, html) {
  tooltip
    .html(html)
    .style("left", event.clientX + 12 + "px")
    .style("top", event.clientY - 10 + "px")
    .style("opacity", 1);
}

export function hideTooltip(tooltip) {
  tooltip.style("opacity", 0);
}

export function addDrag(simulation) {
  return d3
    .drag()
    .on("start", (event, d) => {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    })
    .on("drag", (event, d) => {
      d.fx = event.x;
      d.fy = event.y;
    })
    .on("end", (event, d) => {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    });
}

export function createLegend(svg, items, { x = 20, y = 20 }) {
  const legend = svg
    .append("g")
    .attr("class", "legend")
    .attr("transform", `translate(${x}, ${y})`);

  items.forEach((item, i) => {
    const row = legend.append("g").attr("transform", `translate(0, ${i * 24})`);

    row
      .append("circle")
      .attr("r", 6)
      .attr("cx", 6)
      .attr("cy", 0)
      .attr("fill", item.color);

    row
      .append("text")
      .attr("x", 20)
      .attr("y", 4)
      .attr("fill", "#94a3b8")
      .attr("font-size", "12px")
      .text(item.label);
  });

  return legend;
}

export function nodeRadius(d) {
  const base = 8;
  if (d.type === "directory") return base + (d.metadata?.file_count || 0) * 0.5;
  if (d.type === "package") return base + 2;
  return base;
}
