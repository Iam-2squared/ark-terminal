import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createHash } from "node:crypto";
import {
  buildValidationNoGoReport,
  verifyResumeBundle,
} from "../../scripts/run_phase57_selector_capacity_v2_resume.mjs";

const safety = {
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  transmitted: false,
};
const sha256 = (value) => createHash("sha256").update(value).digest("hex");
const writeArtifact = (root, name, value) => {
  const file = path.join(root, name);
  const bytes = JSON.stringify(value, null, 2) + "\n";
  fs.writeFileSync(file, bytes);
  fs.writeFileSync(`${file}.sha256`, `${sha256(bytes)}  ${name}\n`);
  return file;
};

test("failed Validation becomes terminal NO-GO without releasing OOS", () => {
  const report = buildValidationNoGoReport({
    sourceRunId: "34153192882",
    sourceHeadSha: "90aec031a262179bca716ec3077f9501de75e380",
    model: { modelDigest: "model", safety },
    freeze: { capacityModelDigest: "model", freezeSha256: "freeze", safety },
    validation: {
      fold: "VALIDATION",
      status: "CAPACITY_V2_VALIDATION_NO_GO",
      pass: false,
      gates: { utilityNonInferior: false },
      safety,
    },
  });
  assert.equal(report.status, "CAPACITY_V2_FINAL_NO_GO");
  assert.equal(report.untouchedOosReleased, false);
  assert.equal(report.untouchedOos, null);
  assert.equal(report.automaticPromotion, false);
});

test("NO-GO finalization refuses a passing Validation result", () => {
  assert.throws(
    () =>
      buildValidationNoGoReport({
        sourceRunId: "1",
        sourceHeadSha: "a".repeat(40),
        model: { modelDigest: "model", safety },
        freeze: {
          capacityModelDigest: "model",
          freezeSha256: "freeze",
          safety,
        },
        validation: { fold: "VALIDATION", pass: true, safety },
      }),
    /requires pass=false/,
  );
});

test("resume bundle rejects OOS release after a failed Validation gate", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "capacity-v2-resume-"));
  const hybrid = JSON.parse(
    fs.readFileSync(
      new URL(
        "../research/phase57-selector-minimal-hybrid-development-model.json",
        import.meta.url,
      ),
    ),
  );
  const allocation = {
    status: "CAPACITY_V2_FRESH_ALLOCATION_MATERIALIZED",
    datasetId: "PHASE57_JQUANTS_CAPACITY_V2_FRESH120_V1",
    counts: {
      development: 60,
      validation: 29,
      untouchedOos: 29,
      reserveRemaining: 162,
    },
    safety,
  };
  const admissionCore = {
    status: "CAPACITY_V2_DATASET_ADMISSION_PASS",
    datasetId: allocation.datasetId,
    sessionCount: 120,
    safety,
  };
  const admission = {
    ...admissionCore,
    admissionSha256: sha256(JSON.stringify(admissionCore)),
  };
  const modelCore = {
    status: "CAPACITY_V2_DEVELOPMENT_MODEL_READY",
    sourceHybridModelDigest: hybrid.modelDigest,
    safety,
  };
  const model = {
    ...modelCore,
    modelDigest: sha256(JSON.stringify(modelCore)),
  };
  const freezeCore = {
    status: "CAPACITY_V2_FROZEN_BEFORE_VALIDATION",
    datasetId: allocation.datasetId,
    admissionSha256: admission.admissionSha256,
    capacityModelDigest: model.modelDigest,
    sourceHybridModelDigest: hybrid.modelDigest,
    safety,
  };
  const freeze = {
    ...freezeCore,
    freezeSha256: sha256(JSON.stringify(freezeCore)),
  };
  const development = {
    status: "CAPACITY_V2_DEVELOPMENT_COMPLETE",
    sessionCount: 60,
    decisionTimestampCount: 1200,
    safety,
  };
  const validation = {
    fold: "VALIDATION",
    status: "CAPACITY_V2_VALIDATION_NO_GO",
    pass: false,
    gates: { utilityNonInferior: false },
    safety,
  };
  const paths = Object.fromEntries(
    Object.entries({
      allocation,
      admission,
      model,
      freeze,
      development,
      validation,
    }).map(([name, value]) => [
      `${name}Path`,
      writeArtifact(root, `${name}.json`, value),
    ]),
  );
  assert.throws(
    () =>
      verifyResumeBundle({
        stage: "oos",
        sourceRunId: "34153192882",
        sourceHeadSha: "90aec031a262179bca716ec3077f9501de75e380",
        developmentSummaryPath: paths.developmentPath,
        ...paths,
      }),
    /OOS forbidden/,
  );
});
