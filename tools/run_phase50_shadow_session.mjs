#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { runShadowSession, verifyShadowReport } from "../predict/shadow/phase50-shadow-session.js";

async function main() {
  const [inputPath, outputPath = "artifacts/phase50-shadow-report.json"] = process.argv.slice(2);
  if (!inputPath) throw new Error("usage: node tools/run_phase50_shadow_session.mjs <input.json> [output.json]");
  const raw = await fs.readFile(inputPath, "utf8");
  const input = JSON.parse(raw);
  const report = runShadowSession(input);
  const verification = verifyShadowReport(report);
  if (report.status !== "SHADOW_COMPLETE" || verification.status !== "VALID") {
    throw new Error(`shadow session blocked: ${JSON.stringify({ reportStatus: report.status, blockers: verification.blockers })}`);
  }
  const target = path.resolve(outputPath);
  await fs.mkdir(path.dirname(target), { recursive: true });
  const temp = `${target}.tmp-${process.pid}`;
  await fs.writeFile(temp, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  await fs.rename(temp, target);
  process.stdout.write(`${target}\n`);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
