import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";

const RESEARCH_ROOT = new URL("../predict/research/", import.meta.url);
const PHASE_A = readJson(
  new URL("phase57-selector-capacity-v2-phase-a.json", RESEARCH_ROOT),
);
const HYBRID_MODEL = readJson(
  new URL(
    "phase57-selector-minimal-hybrid-development-model.json",
    RESEARCH_ROOT,
  ),
);
const SAFETY = PHASE_A.safety;
const ALLOWED_STAGES = new Set([
  "validation",
  "oos",
  "finalize_validation_no_go",
]);
const sha256 = (value) => createHash("sha256").update(value).digest("hex");

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}
function writeJson(directory, name, value) {
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  const bytes = JSON.stringify(value, null, 2) + "\n";
  fs.writeFileSync(path.join(directory, name), bytes, { mode: 0o600 });
  fs.writeFileSync(
    path.join(directory, `${name}.sha256`),
    `${sha256(bytes)}  ${name}\n`,
    { mode: 0o600 },
  );
}
function assert(condition, message) {
  if (!condition) throw new Error(message);
}
function digestWithout(value, key) {
  const clone = { ...value };
  delete clone[key];
  return sha256(JSON.stringify(clone));
}
function assertSafety(safety) {
  for (const [key, value] of Object.entries(SAFETY))
    assert(
      value === false && safety?.[key] === false,
      `resume safety mismatch: ${key}`,
    );
}
function assertSidecar(file) {
  const line = fs.readFileSync(`${file}.sha256`, "utf8").trim();
  const [expected, name] = line.split(/\s+/, 2);
  assert(
    name === path.basename(file),
    `resume sidecar filename mismatch: ${file}`,
  );
  assert(
    expected === sha256(fs.readFileSync(file)),
    `resume sidecar digest mismatch: ${file}`,
  );
}

export function verifyResumeBundle({
  stage,
  sourceRunId,
  sourceHeadSha,
  allocationPath,
  admissionPath,
  modelPath,
  freezePath,
  developmentSummaryPath,
  validationPath,
} = {}) {
  assert(ALLOWED_STAGES.has(stage), `unsupported resume stage: ${stage}`);
  assert(
    /^\d+$/.test(String(sourceRunId ?? "")),
    "source run id must be numeric",
  );
  assert(
    /^[0-9a-f]{40}$/.test(String(sourceHeadSha ?? "")),
    "source head SHA must be full lowercase SHA-1",
  );
  const required = [
    allocationPath,
    admissionPath,
    modelPath,
    freezePath,
    developmentSummaryPath,
  ];
  if (stage !== "validation") required.push(validationPath);
  for (const file of required) {
    assert(file && fs.existsSync(file), `resume input missing: ${file}`);
    assertSidecar(file);
  }

  const allocation = readJson(allocationPath),
    admission = readJson(admissionPath),
    model = readJson(modelPath),
    freeze = readJson(freezePath),
    development = readJson(developmentSummaryPath);
  assert(
    allocation.status === "CAPACITY_V2_FRESH_ALLOCATION_MATERIALIZED",
    "resume allocation status mismatch",
  );
  assert(
    allocation.datasetId === "PHASE57_JQUANTS_CAPACITY_V2_FRESH120_V1",
    "resume dataset identity mismatch",
  );
  assert(
    allocation.counts?.development === 60 &&
      allocation.counts?.validation === 29 &&
      allocation.counts?.untouchedOos === 29 &&
      allocation.counts?.reserveRemaining === 162,
    "resume allocation counts mismatch",
  );
  assert(
    admission.status === "CAPACITY_V2_DATASET_ADMISSION_PASS" &&
      admission.datasetId === allocation.datasetId &&
      admission.sessionCount === 120,
    "resume admission mismatch",
  );
  assert(
    admission.admissionSha256 === digestWithout(admission, "admissionSha256"),
    "resume admission digest mismatch",
  );
  assert(
    model.status === "CAPACITY_V2_DEVELOPMENT_MODEL_READY" &&
      model.sourceHybridModelDigest === HYBRID_MODEL.modelDigest,
    "resume model ancestry mismatch",
  );
  assert(
    model.modelDigest === digestWithout(model, "modelDigest"),
    "resume model digest mismatch",
  );
  assert(
    freeze.status === "CAPACITY_V2_FROZEN_BEFORE_VALIDATION" &&
      freeze.datasetId === allocation.datasetId,
    "resume freeze identity mismatch",
  );
  assert(
    freeze.admissionSha256 === admission.admissionSha256 &&
      freeze.capacityModelDigest === model.modelDigest &&
      freeze.sourceHybridModelDigest === HYBRID_MODEL.modelDigest,
    "resume freeze ancestry mismatch",
  );
  assert(
    freeze.freezeSha256 === digestWithout(freeze, "freezeSha256"),
    "resume freeze digest mismatch",
  );
  assert(
    development.status === "CAPACITY_V2_DEVELOPMENT_COMPLETE" &&
      development.sessionCount === 60 &&
      development.decisionTimestampCount === 1200,
    "resume development summary mismatch",
  );
  for (const item of [allocation, admission, model, freeze, development])
    assertSafety(item.safety);

  let validation = null;
  if (stage !== "validation") {
    validation = readJson(validationPath);
    assert(
      validation.fold === "VALIDATION" &&
        /^CAPACITY_V2_VALIDATION_(GO|NO_GO)$/.test(validation.status),
      "resume validation identity mismatch",
    );
    assert(
      validation.pass === Object.values(validation.gates ?? {}).every(Boolean),
      "resume validation gate mismatch",
    );
    assertSafety(validation.safety);
    if (stage === "oos")
      assert(
        validation.pass === true,
        "resume OOS forbidden because Validation did not pass",
      );
    if (stage === "finalize_validation_no_go")
      assert(
        validation.pass === false,
        "NO-GO finalization requires a failed Validation gate",
      );
  }
  return {
    schemaVersion: 1,
    status: "CAPACITY_V2_RESUME_INPUTS_VERIFIED",
    stage,
    sourceRunId: String(sourceRunId),
    sourceHeadSha,
    datasetId: allocation.datasetId,
    admissionSha256: admission.admissionSha256,
    capacityModelDigest: model.modelDigest,
    freezeSha256: freeze.freezeSha256,
    sourceValidationGate: validation
      ? validation.pass
        ? "PASS"
        : "FAIL"
      : "NOT_APPLICABLE",
    oosReleased: false,
    automaticPromotion: false,
    safety: SAFETY,
  };
}

export function buildValidationNoGoReport({
  sourceRunId,
  sourceHeadSha,
  model,
  freeze,
  validation,
} = {}) {
  assert(
    validation?.fold === "VALIDATION" && validation.pass === false,
    "Validation NO-GO report requires pass=false",
  );
  assert(
    model?.modelDigest === freeze?.capacityModelDigest,
    "Validation NO-GO model/freeze mismatch",
  );
  assertSafety(model.safety);
  assertSafety(freeze.safety);
  assertSafety(validation.safety);
  return {
    schemaVersion: 1,
    phase: "57.selector-capacity-v2.final",
    status: "CAPACITY_V2_FINAL_NO_GO",
    reason: "VALIDATION_GATE_FAILED",
    sourceRunId: String(sourceRunId),
    sourceHeadSha,
    validation,
    untouchedOos: null,
    untouchedOosReleased: false,
    capacityModelDigest: model.modelDigest,
    freezeSha256: freeze.freezeSha256,
    reserveRemaining: 162,
    automaticPromotion: false,
    safety: SAFETY,
  };
}

function envBundle(stage) {
  return {
    stage,
    sourceRunId: process.env.SOURCE_RUN_ID,
    sourceHeadSha: process.env.SOURCE_HEAD_SHA,
    allocationPath: process.env.ALLOCATION_PATH,
    admissionPath: process.env.ADMISSION_PATH,
    modelPath: process.env.MODEL_PATH,
    freezePath: process.env.FREEZE_PATH,
    developmentSummaryPath: process.env.DEVELOPMENT_SUMMARY_PATH,
    validationPath: process.env.VALIDATION_PATH,
  };
}
function modeVerify() {
  const manifest = verifyResumeBundle(envBundle(process.env.RESUME_FROM));
  writeJson(
    "artifacts/phase57-capacity-v2-resume-integrity",
    "resume-manifest.json",
    manifest,
  );
  console.log(
    JSON.stringify({
      status: manifest.status,
      stage: manifest.stage,
      sourceValidationGate: manifest.sourceValidationGate,
      freezeSha256: manifest.freezeSha256,
    }),
  );
}
function modeFinalizeNoGo() {
  verifyResumeBundle(envBundle("finalize_validation_no_go"));
  const report = buildValidationNoGoReport({
    sourceRunId: process.env.SOURCE_RUN_ID,
    sourceHeadSha: process.env.SOURCE_HEAD_SHA,
    model: readJson(process.env.MODEL_PATH),
    freeze: readJson(process.env.FREEZE_PATH),
    validation: readJson(process.env.VALIDATION_PATH),
  });
  writeJson(
    "artifacts/phase57-capacity-v2-final",
    "final-summary.json",
    report,
  );
  console.log(
    JSON.stringify({
      status: report.status,
      reason: report.reason,
      untouchedOosReleased: false,
      freezeSha256: report.freezeSha256,
    }),
  );
}

async function main() {
  const mode = process.argv[2];
  if (mode === "verify") return modeVerify();
  if (mode === "finalize-validation-no-go") return modeFinalizeNoGo();
  throw new Error("mode must be verify|finalize-validation-no-go");
}
if (
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
)
  main().catch((error) => {
    console.error(`CAPACITY_V2_RESUME_FAIL ${String(error?.message ?? error)}`);
    process.exitCode = 1;
  });
