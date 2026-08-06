#!/usr/bin/env node
import { promises as fs } from "node:fs";
import path from "node:path";
import process from "node:process";
import { buildPhase45PersistencePlan } from "../predict/data/phase45-persistence.js";

function parseArgs(argv) {
  const options = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    options[key] = argv[index + 1] && !argv[index + 1].startsWith("--") ? argv[++index] : "true";
  }
  return options;
}

function parseCsv(text) {
  const lines = text.replace(/^\uFEFF/, "").split(/\r?\n/).filter((line) => line.trim());
  if (!lines.length) return [];
  const headers = lines[0].split(",").map((item) => item.trim());
  return lines.slice(1).map((line) => {
    const values = line.split(",");
    return Object.fromEntries(headers.map((header, index) => [header, values[index]?.trim() ?? ""]));
  });
}

async function readRecords(filePath) {
  const raw = await fs.readFile(filePath, "utf8");
  if (path.extname(filePath).toLowerCase() === ".csv") return parseCsv(raw);
  const parsed = JSON.parse(raw);
  return Array.isArray(parsed) ? parsed : parsed.rows ?? parsed.records ?? [];
}

async function readJsonIfExists(filePath) {
  try {
    return JSON.parse(await fs.readFile(filePath, "utf8"));
  } catch (error) {
    if (error?.code === "ENOENT") return null;
    throw error;
  }
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

  const outputDir = path.resolve(args["output-dir"] || "data/data-lake");
  const shardPath = path.join(outputDir, "shards", "latest.json");
  const manifestPath = path.join(outputDir, "manifest.json");
  const checkpointPath = path.join(outputDir, "checkpoint.json");
  const rejectedPath = path.join(outputDir, "rejected.json");

  const records = await readRecords(path.resolve(args.input));
  const existingShard = await readJsonIfExists(shardPath);
  const plan = buildPhase45PersistencePlan({
    records,
    provider: args.provider || "GENERIC",
    existingShard,
    runId: args["run-id"],
  });

  if (plan.status !== "READY_TO_PERSIST") {
    await atomicWriteJson(rejectedPath, {
      status: plan.status,
      blockers: plan.batch?.inspection?.blockers ?? [],
      warnings: plan.batch?.inspection?.warnings ?? [],
      safety: plan.safety,
    });
    throw new Error("PHASE45_PIPELINE_BLOCKED");
  }

  await atomicWriteJson(shardPath, plan.ingestionPlan.merged.shard);
  await atomicWriteJson(manifestPath, plan.ingestionPlan.manifest);
  await atomicWriteJson(checkpointPath, plan.checkpoint);
  await atomicWriteJson(rejectedPath, { rejected: [], safety: plan.safety });

  console.log(JSON.stringify({
    status: plan.status,
    recordCount: plan.ingestionPlan.merged.shard.recordCount,
    insertedCount: plan.ingestionPlan.merged.insertedKeys.length,
    updatedCount: plan.ingestionPlan.merged.updatedKeys.length,
    staleIgnoredCount: plan.ingestionPlan.merged.ignoredStaleKeys.length,
    brokerWrites: 0,
    excelOrderWrites: 0,
    rssOrderCalls: 0,
    liveOrders: 0,
  }, null, 2));
}

main().catch((error) => {
  console.error(error?.stack || String(error));
  process.exitCode = 1;
});
