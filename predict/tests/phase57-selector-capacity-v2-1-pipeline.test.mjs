import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

import { Phase57CapacityV21Internals as I } from "../../scripts/run_phase57_selector_capacity_v2_1.mjs";

const research = new URL("../research/", import.meta.url);
const pilot = new Set(
  JSON.parse(
    fs.readFileSync(
      new URL(
        "phase57-selector-source-validation-only-registry.json",
        research,
      ),
      "utf8",
    ),
  ).sessions.map((row) => row.sessionDate),
);
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

function dates(count) {
  const result = [];
  let cursor = new Date("2025-04-15T00:00:00Z");
  while (result.length < count) {
    const date = cursor.toISOString().slice(0, 10);
    if (!pilot.has(date)) result.push(date);
    cursor = new Date(cursor.getTime() + 86400000);
  }
  return result;
}
function sourceAllocation(all) {
  return {
    status: "CAPACITY_V2_FRESH_ALLOCATION_MATERIALIZED",
    datasetId: "PHASE57_JQUANTS_CAPACITY_V2_FRESH120_V1",
    development: all.slice(0, 60),
    purgeDevelopmentValidation: all.slice(60, 61),
    validation: all.slice(61, 90),
    purgeValidationOos: all.slice(90, 91),
    untouchedOos: all.slice(91, 120),
  };
}

test("v2.1 allocates only precommitted post-120 reserve ordinals", () => {
  const all = dates(282),
    allocation = I.buildV21Allocation(
      all.map((Date) => ({ Date, HolDiv: "1" })),
      sourceAllocation(all),
    );
  assert.deepEqual(allocation.freshValidation, all.slice(120, 149));
  assert.deepEqual(allocation.purgeValidationOos, all.slice(149, 150));
  assert.deepEqual(allocation.freshUntouchedOos, all.slice(150, 179));
  assert.equal(allocation.remainingReserve.sessionCount, 103);
  assert.equal(allocation.quarantinedOriginalOos.reused, false);
});

function syntheticRows() {
  const rows = [];
  for (let session = 0; session < 89; session += 1) {
    const date = `2025-${String(Math.floor(session / 28) + 1).padStart(2, "0")}-${String((session % 28) + 1).padStart(2, "0")}`;
    for (let decision = 0; decision < 20; decision += 1) {
      const index = session * 20 + decision;
      rows.push({
        sessionDate: date,
        featureCutoff: `${date}T${String(9 + Math.floor(decision / 6)).padStart(2, "0")}:${String((decision % 6) * 5).padStart(2, "0")}:00.000Z`,
        features: {
          hybridQualityDecayRank5To1: (index % 17) / 17,
          qualifiedCandidateCount: 10 + (index % 7),
          marketBreadth: 0.3 + (index % 5) / 10,
          dataQualityConfidence: 0.9 + (index % 3) / 100,
        },
        targets: { RANK_6_10: 20, RANK_11_15: 15, RANK_16_20: 10 },
        utilityByCapacity: Object.fromEntries(
          Array.from({ length: 20 }, (_, i) => [i + 1, 100 + i + 1]),
        ),
        frozenSelectedCount: 5,
        frozenSelectedUtility: 105,
        rankedCount: 20,
        prefixIdentity: true,
        modelDigest:
          "444e296d31b0e59263f268706b4c8a7c7e9e59d6f7c9547e9f90342a24040fc2",
      });
    }
  }
  return rows;
}

test("v2.1 trains on 89 sessions and selects mapping from held-out predictions", () => {
  const result = I.trainV21(
    syntheticRows(),
    { admissionSha256: "source" },
    { admissionSha256: "fresh" },
    { datasetId: "PHASE57_JQUANTS_CAPACITY_V2_1_FRESH59_V1" },
  );
  assert.equal(result.summary.sessionCount, 89);
  assert.equal(result.summary.oofDecisionTimestampCount, 880);
  assert.equal(
    result.model.guards.thresholdSelectionUsesOnlyHeldOutPredictions,
    true,
  );
  assert.ok(
    result.model.developmentSelection.worstFoldUtilityDifference >= -10,
  );
  assert.equal(result.freeze.validationReleased, false);
  assert.equal(result.freeze.untouchedOosReleased, false);
  assert.ok(
    Object.values(result.freeze.safety).every((value) => value === false),
  );
});

test("v2.1 fresh admission rejects missing shards", () => {
  const root = fs.mkdtempSync("/tmp/capacity-v21-admission-");
  const allocation = {
    freshValidation: [],
    purgeValidationOos: [],
    freshUntouchedOos: [],
  };
  assert.throws(
    () => I.summarizeAdmission({ allocation, inputRoot: root }),
    /admission incomplete/,
  );
});

test("v2.1 workflow releases OOS only after a successful Validation gate", () => {
  const workflow = fs.readFileSync(
    new URL(
      "../../.github/workflows/phase57-selector-capacity-v2-1.yml",
      import.meta.url,
    ),
    "utf8",
  );
  assert.match(workflow, /if: needs\.validation\.outputs\.gate == 'PASS'/);
  assert.match(
    workflow,
    /if: always\(\) && needs\.validation\.result == 'success' && needs\.validation\.outputs\.gate == 'FAIL'/,
  );
  assert.match(
    workflow,
    /Finaliz[e] fresh Validation NO-GO without OOS release/,
  );
  assert.doesNotMatch(workflow, /automaticPromotionAllowed:\s*true/);
});
