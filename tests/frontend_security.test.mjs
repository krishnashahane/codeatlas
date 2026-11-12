import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { escapeHtml } from "../src/utils/graphHelpers.js";

test("repository-controlled tooltip values are HTML escaped", () => {
  const payload = '<img src=x onerror="alert(1)">&' + "'";
  assert.equal(
    escapeHtml(payload),
    "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;&amp;&#39;",
  );
});

test("nullish tooltip values do not produce unsafe markup", () => {
  assert.equal(escapeHtml(null), "");
  assert.equal(escapeHtml(undefined), "");
  assert.equal(escapeHtml(42), "42");
});

test("all D3 tooltip components escape repository-controlled values", () => {
  const architecture = fs.readFileSync(
    new URL("../src/components/ArchitectureMap.jsx", import.meta.url),
    "utf8",
  );
  const dependencies = fs.readFileSync(
    new URL("../src/components/DependencyGraph.jsx", import.meta.url),
    "utf8",
  );
  const knowledge = fs.readFileSync(
    new URL("../src/components/KnowledgeGraph.jsx", import.meta.url),
    "utf8",
  );

  assert.match(architecture, /escapeHtml\(d\.label\)/);
  assert.match(architecture, /escapeHtml\(d\.metadata\?\.layer/);
  assert.match(dependencies, /escapeHtml\(d\.label\)/);
  assert.match(dependencies, /escapeHtml\(d\.metadata\?\.module/);
  assert.match(knowledge, /escapeHtml\(d\.label\)/);
  assert.match(knowledge, /\.map\(escapeHtml\)/);
});
