#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { auditPaperForwardCycle, buildPaperForwardCycle } from "../predict/paper/phase49-paper-forward.js";

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : fallback;
}

const inputPath = arg("input");
const outputPath = arg("output", "data/phase49-paper-forward.json");
if (!inputPath) {
  console.error("Usage: node tools/run_phase49_paper_forward.mjs --input <json> [--output <json>]");
  process.exit(2);
}

const raw = JSON.parse(await fs.readFile(inputPath, "utf8"));
const cycle = buildPaperForwardCycle(raw);
const audit = auditPaperForwardCycle(cycle);
if (audit.status !== "VALID") {
  console.error(JSON.stringify(audit, null, 2));
  process.exit(1);
}

await fs.mkdir(path.dirname(outputPath), { recursive: true });
const temp = `${outputPath}.tmp-${process.pid}`;
await fs.writeFile(temp, `${JSON.stringify(cycle, null, 2)}\n`, "utf8");
await fs.rename(temp, outputPath);
console.log(JSON.stringify({ status: cycle.status, tradeCount: cycle.summary.tradeCount, outputPath }, null, 2));
