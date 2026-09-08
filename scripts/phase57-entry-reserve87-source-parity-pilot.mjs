import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { Phase57FreshSessionInternals } from "./lib/phase57-selector-jquants-fresh-session.mjs";

const sha256 = (value) => createHash("sha256").update(value).digest("hex");
const MANIFEST_PATH = process.env.RECOVERY_MANIFEST_PATH ?? "predict/research/phase57-entry-reserve87-formal-recovery.json";
const ADMISSION_V2 = process.env.ADMISSION_V2_PATH ?? "artifacts/input/admission-v2/admission.json";
const ADMISSION_V21 = process.env.ADMISSION_V21_PATH ?? "artifacts/input/admission-v21/admission.json";
const OUT_DIR = process.env.OUTPUT_DIR ?? "artifacts/phase57-entry-reserve87-source-parity-pilot";
const API_KEY = process.env.JQUANTS_API_KEY ?? "";

function readJson(file) { return JSON.parse(fs.readFileSync(file, "utf8")); }
function assert(condition, message) { if (!condition) throw new Error(message); }
function safeError(error) { return String(error?.message ?? error).replace(/[A-Za-z0-9_-]{24,}/g, "[REDACTED]"); }
function writeJson(name, value) {
  fs.mkdirSync(OUT_DIR, { recursive: true, mode: 0o700 });
  const text = JSON.stringify(value, null, 2) + "\n";
  fs.writeFileSync(path.join(OUT_DIR, name), text, { mode: 0o600 });
  fs.writeFileSync(path.join(OUT_DIR, `${name}.sha256`), `${sha256(text)}  ${name}\n`, { mode: 0o600 });
}

const manifest = readJson(MANIFEST_PATH);
assert(manifest?.status === "FORMAL_ALLOCATION_RECOVERED_SOURCE_PARITY_PILOT_PRECOMMITTED", "recovery manifest not frozen");
assert(manifest?.pilot?.precommittedBeforeRefetch === true, "pilot not precommitted");
assert(manifest?.pilot?.purpose === "ENTRY_DEV_SOURCE_PARITY_ONLY_NO_FEATURES_NO_LABELS_NO_OUTCOMES", "pilot scope mismatch");
assert(manifest?.pilot?.fold === "PURGE", "pilot must use PURGE fold");
assert(String(API_KEY).trim(), "JQUANTS_API_KEY_REQUIRED");

const admissions = [readJson(ADMISSION_V2), readJson(ADMISSION_V21)];
const expectedByDate = new Map(admissions.flatMap((item) => item.auditBySession ?? []).map((row) => [row.sessionDate, row]));
const results = [];
let pass = true;

for (const sessionDate of manifest.pilot.sessions) {
  const expected = expectedByDate.get(sessionDate);
  assert(expected, `missing expected admission ${sessionDate}`);
  try {
    const { structuralAudit } = await Phase57FreshSessionInternals.loadFreshSession({
      apiKey: API_KEY,
      date: sessionDate,
      fold: "PURGE",
    });
    const parity = {};
    for (const key of manifest.pilot.requiredParity) {
      parity[key] = {
        expected: expected[key],
        actual: structuralAudit[key],
        match: expected[key] === structuralAudit[key],
      };
    }
    const allMatch = Object.values(parity).every((item) => item.match);
    pass &&= allMatch;
    results.push({
      sessionDate,
      status: allMatch ? "SOURCE_PARITY_PASS" : "SOURCE_PARITY_MISMATCH",
      parity,
      eligibleJpxSymbolCount: { expected: expected.eligibleJpxSymbolCount, actual: structuralAudit.eligibleJpxSymbolCount },
      normalizedMinuteRows: { expected: expected.normalizedMinuteRows, actual: structuralAudit.normalizedMinuteRows },
      fiveMinuteBars: { expected: expected.fiveMinuteBars, actual: structuralAudit.fiveMinuteBars },
      featureCalculationPerformed: structuralAudit.featureCalculationPerformed,
      labelGenerationPerformed: structuralAudit.labelGenerationPerformed,
      outcomeInspectionPerformed: structuralAudit.outcomeInspectionPerformed,
      rawPersisted: structuralAudit.rawPersisted,
    });
  } catch (error) {
    pass = false;
    results.push({ sessionDate, status: "SOURCE_PARITY_ERROR", error: safeError(error) });
  }
}

const output = {
  schemaVersion: 1,
  phase: "57.entry.minimal-stateful.reserve87.source-parity-pilot",
  status: pass ? "SOURCE_PARITY_PILOT_PASS" : "SOURCE_PARITY_PILOT_FAIL",
  purpose: manifest.pilot.purpose,
  sessions: manifest.pilot.sessions,
  results,
  developmentUnlocked: false,
  featureCalculationPerformed: false,
  labelGenerationPerformed: false,
  outcomeInspectionPerformed: false,
  reserve180To282Opened: 0,
  freshValidationOpened: 0,
  freshOosOpened: 0,
  safety: manifest.safety,
};
writeJson("source-parity-pilot.json", output);
if (!pass) process.exitCode = 20;
