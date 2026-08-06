import { buildPhase41IngestionPlan, createPhase41Checkpoint } from "./phase41-ingestion.js";
import { buildHistoricalIngestionBatch, PHASE45_SAFETY } from "./phase45-historical-data.js";

function text(value) {
  return String(value ?? "").trim();
}

export function buildPhase45PersistencePlan({ records = [], provider = "GENERIC", existingShard = null, runId } = {}) {
  const batch = buildHistoricalIngestionBatch({ records, provider });
  if (batch.status !== "READY_FOR_PHASE41") {
    return Object.freeze({
      status: "BLOCKED",
      batch,
      ingestionPlan: null,
      checkpoint: null,
      brokerWrites: 0,
      excelOrderWrites: 0,
      rssOrderCalls: 0,
      liveOrders: 0,
      safety: PHASE45_SAFETY,
    });
  }

  const ingestionPlan = buildPhase41IngestionPlan({
    existingShard,
    batches: [{ provider: batch.provider, rows: batch.records }],
  });

  if (ingestionPlan.integrity.status !== "VALID" || ingestionPlan.status === "REVIEW_REQUIRED") {
    return Object.freeze({
      status: "BLOCKED",
      batch,
      ingestionPlan,
      checkpoint: null,
      brokerWrites: 0,
      excelOrderWrites: 0,
      rssOrderCalls: 0,
      liveOrders: 0,
      safety: PHASE45_SAFETY,
    });
  }

  const checkpoint = createPhase41Checkpoint({
    plan: ingestionPlan,
    runId: text(runId) || `phase45-${Date.now()}`,
  });

  return Object.freeze({
    status: "READY_TO_PERSIST",
    batch,
    ingestionPlan,
    checkpoint,
    brokerWrites: 0,
    excelOrderWrites: 0,
    rssOrderCalls: 0,
    liveOrders: 0,
    safety: PHASE45_SAFETY,
  });
}
