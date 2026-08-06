#!/usr/bin/env node
import { promises as fs } from "node:fs";
import path from "node:path";
import process from "node:process";
import { auditPhase47Candidate, buildPhase47RegistryCandidate, runWalkForward } from "../predict/models/phase47-walk-forward.js";

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    const value = argv[index + 1] && !argv[index + 1].startsWith("--") ? argv[++index] : "true";
    result[key] = value;
  }
  return result;
}

async function atomicWriteJson(filePath, value) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  const temporary = `${filePath}.tmp-${process.pid}`;
  await fs.writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  await fs.rename(temporary, filePath);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.input) throw new Error("--input is required");
  const output = path.resolve(args.output || "data/models/phase47-candidate.json");
  const parsed = JSON.parse(await fs.readFile(path.resolve(args.input), "utf8"));
  const rows = Array.isArray(parsed) ? parsed : parsed.rows ?? parsed.dataset?.rows ?? [];
  const datasetLineage = parsed.lineage ?? parsed.datasetLineage ?? {};
  const walkForward = runWalkForward({
    rows,
    costRate: Number(args["cost-rate"] ?? 0.001),
    options: {
      minTrain: Number(args["min-train"] ?? 60),
      validationSize: Number(args["validation-size"] ?? 20),
      step: Number(args.step ?? 20),
    },
  });
  const candidate = buildPhase47RegistryCandidate({ rows, walkForwardResult: walkForward, datasetLineage });
  const audit = auditPhase47Candidate(candidate);
  if (audit.status !== "READY_FOR_HUMAN_REVIEW") {
    throw new Error(`PHASE47_CANDIDATE_BLOCKED:${audit.blockers.join(",")}`);
  }
  await atomicWriteJson(output, { candidate, audit, walkForward });
  console.log(JSON.stringify({
    status: audit.status,
    output,
    selectedModelType: walkForward.selectedModelType,
    folds: walkForward.folds,
    brokerWrites: 0,
    excelOrderWrites: 0,
    rssOrderCalls: 0,
    liveOrders: 0,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
  }, null, 2));
}

main().catch((error) => {
  console.error(error?.stack || String(error));
  process.exitCode = 1;
});
