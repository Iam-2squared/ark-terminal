#!/usr/bin/env node
import { promises as fs } from "node:fs";
import path from "node:path";
import process from "node:process";
import {
  auditAdvancedDataset,
  buildDatasetLineage,
  generateExtendedFeatures,
  splitDatasetByTime,
} from "../predict/features/phase46-advanced-dataset.js";

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 1) {
    if (!argv[i].startsWith("--")) continue;
    const key = argv[i].slice(2);
    out[key] = argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[++i] : "true";
  }
  return out;
}

async function atomicWrite(filePath, value) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  const temp = `${filePath}.tmp-${process.pid}`;
  await fs.writeFile(temp, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  await fs.rename(temp, filePath);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.input) throw new Error("--input is required");
  if (!args["dataset-version"]) throw new Error("--dataset-version is required");
  if (!args["source-manifest-checksum"]) throw new Error("--source-manifest-checksum is required");

  const raw = JSON.parse(await fs.readFile(path.resolve(args.input), "utf8"));
  const records = Array.isArray(raw) ? raw : raw.records ?? raw.rows ?? [];
  const rows = generateExtendedFeatures(records);
  const split = splitDatasetByTime(rows);
  const lineage = buildDatasetLineage({
    datasetVersion: args["dataset-version"],
    sourceManifestChecksum: args["source-manifest-checksum"],
    rows,
  });
  const audit = auditAdvancedDataset({ rows, split, lineage });
  if (audit.status !== "VALID") throw new Error(`DATASET_BLOCKED:${audit.blockers.join(",")}`);

  const output = {
    datasetVersion: args["dataset-version"],
    rows,
    split: {
      train: split.train,
      validation: split.validation,
      test: split.test,
      temporalOrderValid: split.temporalOrderValid,
    },
    lineage,
    audit,
  };
  const outputPath = path.resolve(args.output || "data/training/phase46-dataset.json");
  await atomicWrite(outputPath, output);
  console.log(JSON.stringify({ status: "VALID", outputPath, rowCount: rows.length, brokerWrites: 0, liveOrders: 0 }, null, 2));
}

main().catch((error) => {
  console.error(error?.stack || String(error));
  process.exitCode = 1;
});
