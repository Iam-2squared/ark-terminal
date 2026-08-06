#!/usr/bin/env node
import { promises as fs } from "node:fs";
import path from "node:path";
import process from "node:process";
import {
  buildPhase41IngestionPlan,
  createPhase41Checkpoint,
} from "../predict/data/phase41-ingestion.js";

function parseArgs(argv) {
  const options = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    const value = argv[index + 1] && !argv[index + 1].startsWith("--") ? argv[++index] : "true";
    options[key] = value;
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

async function readSourceFile(filePath, defaults = {}) {
  const extension = path.extname(filePath).toLowerCase();
  const raw = await fs.readFile(filePath, "utf8");
  const parsed = extension === ".csv" ? parseCsv(raw) : JSON.parse(raw);
  const rows = Array.isArray(parsed) ? parsed : parsed.rows ?? parsed.records ?? [];
  return {
    provider: extension === ".csv" ? "CSV" : "JSON",
    rows,
    metadata: {
      symbol: defaults.symbol,
      kind: defaults.kind,
      source: defaults.source || path.basename(filePath),
      updatedAt: defaults.updatedAt,
      currency: defaults.currency,
    },
  };
}

async function atomicWriteJson(filePath, value) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  const temporary = `${filePath}.tmp-${process.pid}`;
  await fs.writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  await fs.rename(temporary, filePath);
}

async function readJsonIfExists(filePath) {
  try {
    return JSON.parse(await fs.readFile(filePath, "utf8"));
  } catch (error) {
    if (error?.code === "ENOENT") return null;
    throw error;
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const input = args.input;
  if (!input) throw new Error("--input is required");

  const outputDir = path.resolve(args["output-dir"] || "data/data-lake");
  const shardPath = path.join(outputDir, "shards", "latest.json");
  const manifestPath = path.join(outputDir, "manifest.json");
  const checkpointPath = path.join(outputDir, "checkpoint.json");
  const rejectedPath = path.join(outputDir, "rejected.json");

  const batch = await readSourceFile(path.resolve(input), {
    symbol: args.symbol,
    kind: args.kind || "OHLCV",
    source: args.source,
    updatedAt: args["updated-at"],
    currency: args.currency || "JPY",
  });
  const existingShard = await readJsonIfExists(shardPath);
  const plan = buildPhase41IngestionPlan({ existingShard, batches: [batch] });
  const checkpoint = createPhase41Checkpoint({ plan, runId: args["run-id"] });

  if (plan.integrity.status !== "VALID") {
    await atomicWriteJson(rejectedPath, { rejected: plan.rejected, integrity: plan.integrity });
    throw new Error(`DATA_LAKE_INTEGRITY_BLOCKED:${plan.integrity.blockers.join(",")}`);
  }

  await atomicWriteJson(shardPath, plan.merged.shard);
  await atomicWriteJson(manifestPath, plan.manifest);
  await atomicWriteJson(checkpointPath, checkpoint);
  await atomicWriteJson(rejectedPath, { rejected: plan.rejected });

  console.log(JSON.stringify({
    status: plan.status,
    outputDir,
    recordCount: plan.merged.shard.recordCount,
    insertedCount: plan.merged.insertedKeys.length,
    updatedCount: plan.merged.updatedKeys.length,
    staleIgnoredCount: plan.merged.ignoredStaleKeys.length,
    rejectedCount: plan.rejected.length,
    brokerWrites: 0,
    liveOrders: 0,
  }, null, 2));
}

main().catch((error) => {
  console.error(error?.stack || String(error));
  process.exitCode = 1;
});
