#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { evaluatePromotionCandidate, verifyPromotionEvaluation } from "../predict/shadow/phase50-7-promotion-evaluation.js";
import { buildDailyShadowHistory, evaluateShadowStability, verifyShadowStability } from "../predict/shadow/phase50-8-stability.js";

const inputPath = process.argv[2] || "data/phase50-shadow/input.json";
const historyPath = process.argv[3] || "data/phase50-shadow/history.json";
const reportPath = process.argv[4] || "data/phase50-shadow/stability.json";

function readJson(file, fallback = null) {
  if (!fs.existsSync(file)) return fallback;
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function atomicWrite(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temp = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(temp, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  fs.renameSync(temp, file);
}

const input = readJson(inputPath);
if (!input) throw new Error(`PHASE50_8_INPUT_MISSING:${inputPath}`);

const evaluation = evaluatePromotionCandidate(input);
const verification = verifyPromotionEvaluation(evaluation);
if (verification.status !== "VALID") throw new Error(`PHASE50_7_SAFETY_BLOCK:${verification.blockers.join(",")}`);

const history = buildDailyShadowHistory({
  previous: readJson(historyPath, []),
  evaluation,
  observedAt: input.observedAt || new Date().toISOString(),
});
const stability = evaluateShadowStability({ history, thresholds: input.stabilityThresholds || {} });
const stabilityVerification = verifyShadowStability(stability);
if (stabilityVerification.status !== "VALID") throw new Error(`PHASE50_8_SAFETY_BLOCK:${stabilityVerification.blockers.join(",")}`);

atomicWrite(historyPath, history);
atomicWrite(reportPath, { evaluation, stability, safetyVerification: { phase50_7: verification, phase50_8: stabilityVerification } });
console.log(JSON.stringify({ status: "OK", historyPath, reportPath, evaluation: evaluation.classification, stability: stability.classification }));
