#!/usr/bin/env node
import { readFile, writeFile, rename, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { buildPhase48EvaluationPayload, auditPhase48Payload } from "../predict/evaluation/phase48-evaluation-payload.js";
import { buildPhase48DashboardView } from "../predict/evaluation/phase48-dashboard-view.js";

const [, , inputPath, outputPath] = process.argv;
if (!inputPath || !outputPath) {
  console.error("usage: node tools/run_phase48_evaluation_payload.mjs <input.json> <output.json>");
  process.exit(2);
}

const source = JSON.parse(await readFile(resolve(inputPath), "utf8"));
const payload = buildPhase48EvaluationPayload(source);
const audit = auditPhase48Payload(payload);
if (audit.status !== "VALID") {
  console.error(JSON.stringify(audit));
  process.exit(1);
}
const result = { payload, dashboard: buildPhase48DashboardView(payload) };
const target = resolve(outputPath);
const temp = `${target}.tmp-${process.pid}`;
await mkdir(dirname(target), { recursive: true });
await writeFile(temp, JSON.stringify(result, null, 2), "utf8");
await rename(temp, target);
console.log(JSON.stringify({ status: "WRITTEN", output: target, checksum: payload.checksum }));
