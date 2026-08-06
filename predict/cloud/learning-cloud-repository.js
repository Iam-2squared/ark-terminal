import {
  listCloudRecords,
  saveCloudRecord,
} from "./cloud-sync-client.js";

export const LEARNING_CLOUD_ARCHIVE_VERSION =
  "learning-cloud-archive-v1";

export const LEARNING_CLOUD_COLLECTIONS = Object.freeze({
  candidates: "candidate_models",
  modelVersions: "model_versions",
  forwardTests: "forward_test_results",
});

const MODEL_AUDIT_ACTIONS = new Set([
  "PRODUCTION_SET",
  "HUMAN_APPROVED",
  "ROLLBACK",
]);

function cleanText(value, maximumLength = 160) {
  return String(value ?? "").trim().slice(0, maximumLength);
}

function normalizedRecordId(value, prefix = "record") {
  const normalized = cleanText(value, 220)
    .replace(/[^A-Za-z0-9._:-]/g, "-")
    .replace(/-+/g, "-")
    .replace(/^[-._:]+/, "")
    .slice(0, 160);

  if (/^[A-Za-z0-9]/.test(normalized)) return normalized;
  return `${prefix}-${Date.now()}`.slice(0, 160);
}

function cloneJson(value) {
  try {
    return JSON.parse(JSON.stringify(value));
  }
  catch {
    throw new Error("LEARNING_ARCHIVE_JSON_REQUIRED");
  }
}

function anyTrue(...values) {
  return values.some((value) => value === true);
}

function requireNoExecutionPermission(source = {}) {
  const safety = source?.safety ?? {};
  const metadata = source?.metadata ?? {};

  if (
    anyTrue(
      source?.productionUpdateAllowed,
      source?.automaticPromotionAllowed,
      source?.brokerWriteAllowed,
      source?.liveTradingAllowed,
      source?.liveBrokerAllowed,
      source?.runtimeActivationAllowed,
      safety?.productionUpdateAllowed,
      safety?.automaticPromotionAllowed,
      safety?.brokerWriteAllowed,
      safety?.liveTradingAllowed,
      safety?.liveBrokerAllowed,
      safety?.runtimeActivationAllowed,
      metadata?.productionUpdateAllowed,
      metadata?.automaticPromotionAllowed,
      metadata?.brokerWriteAllowed,
      metadata?.liveTradingAllowed,
      metadata?.runtimeActivationAllowed,
    )
  ) {
    throw new Error("LEARNING_ARCHIVE_EXECUTION_PERMISSION_REJECTED");
  }
}

function humanApprovalRequired(source = {}) {
  return Boolean(
    source?.humanApprovalRequired === true ||
    source?.safety?.humanApprovalRequired === true ||
    source?.metadata?.humanApprovalRequired === true,
  );
}

function archiveSafety() {
  return {
    advisoryOnly: true,
    humanApprovalRequired: true,
    automaticPromotionAllowed: false,
    runtimeActivationAllowed: false,
    productionUpdateAllowed: false,
    brokerWriteAllowed: false,
    liveTradingAllowed: false,
  };
}

export function buildCandidateArchiveRecord({
  candidate,
  action = "CANDIDATE_STATE_CHANGED",
} = {}) {
  if (!candidate || typeof candidate !== "object") {
    throw new Error("SAFE_CANDIDATE_REQUIRED");
  }

  requireNoExecutionPermission(candidate);

  if (!humanApprovalRequired(candidate)) {
    throw new Error("CANDIDATE_HUMAN_APPROVAL_REQUIRED");
  }

  const id = normalizedRecordId(candidate.id, "candidate");
  const version = cleanText(
    candidate.version ?? candidate.candidateVersion,
    120,
  );

  if (!id || !version) {
    throw new Error("CANDIDATE_ID_AND_VERSION_REQUIRED");
  }

  const data = cloneJson({
    archiveVersion: LEARNING_CLOUD_ARCHIVE_VERSION,
    archiveType: "CANDIDATE",
    action: cleanText(action, 80) || "CANDIDATE_STATE_CHANGED",
    id,
    version,
    status: cleanText(candidate.status, 80) || "UNKNOWN",
    createdAt: candidate.createdAt ?? null,
    updatedAt:
      candidate.updatedAt ??
      candidate.approvedAt ??
      candidate.walkForward?.completedAt ??
      candidate.createdAt ??
      new Date().toISOString(),
    sourceTradeCount: Number(candidate.sourceTradeCount) || 0,
    weights: candidate.weights ?? {},
    thresholds: candidate.thresholds ?? candidate.metadata?.thresholds ?? {},
    calibration: candidate.calibration ?? null,
    drift: candidate.drift ?? null,
    walkForward: candidate.walkForward ?? null,
    comparison: candidate.comparison ?? null,
    metadata: candidate.metadata ?? {},
    safety: archiveSafety(),
  });

  return {
    collection: LEARNING_CLOUD_COLLECTIONS.candidates,
    id,
    data,
  };
}

export function buildForwardValidationArchiveRecord({
  result,
  candidateId,
} = {}) {
  if (!result || typeof result !== "object") {
    throw new Error("SAFE_FORWARD_VALIDATION_RESULT_REQUIRED");
  }

  requireNoExecutionPermission(result);

  if (result?.safety?.humanApprovalRequired !== true) {
    throw new Error("FORWARD_VALIDATION_HUMAN_APPROVAL_REQUIRED");
  }

  const resolvedCandidateId = cleanText(
    candidateId ??
    result?.candidate?.proposalId ??
    result?.candidate?.version,
    160,
  );

  if (!resolvedCandidateId) {
    throw new Error("FORWARD_VALIDATION_CANDIDATE_REQUIRED");
  }

  const generatedAt =
    result.generatedAt ??
    new Date().toISOString();
  const id = normalizedRecordId(
    `forward-${resolvedCandidateId}-${generatedAt}`,
    "forward",
  );

  const data = cloneJson({
    archiveVersion: LEARNING_CLOUD_ARCHIVE_VERSION,
    archiveType: "FORWARD_VALIDATION",
    id,
    candidateId: resolvedCandidateId,
    generatedAt,
    status: cleanText(result.status, 100) || "UNKNOWN",
    validationContext: result.validationContext ?? {},
    diagnostics: result.diagnostics ?? {},
    championModel: result.championModel ?? null,
    candidate: result.candidate ?? null,
    championAudit: result.championAudit ?? null,
    challengerAudit: result.challengerAudit ?? null,
    evaluation: result.evaluation ?? null,
    blockers: Array.isArray(result.blockers) ? result.blockers : [],
    safety: archiveSafety(),
  });

  return {
    collection: LEARNING_CLOUD_COLLECTIONS.forwardTests,
    id,
    data,
  };
}

export function buildModelVersionArchiveRecord({
  action,
  model,
  candidateId = null,
  approvedBy = null,
  note = null,
  at = null,
} = {}) {
  const normalizedAction = cleanText(action, 80).toUpperCase();

  if (!MODEL_AUDIT_ACTIONS.has(normalizedAction)) {
    throw new Error("MODEL_AUDIT_ACTION_NOT_ALLOWED");
  }

  if (!model || typeof model !== "object") {
    throw new Error("MODEL_VERSION_REQUIRED");
  }

  requireNoExecutionPermission(model);

  const version = cleanText(model.version, 120);
  if (!version) throw new Error("MODEL_VERSION_REQUIRED");

  const actor = cleanText(
    approvedBy ?? model.approvedBy,
    120,
  );

  if (["HUMAN_APPROVED", "ROLLBACK"].includes(normalizedAction) && !actor) {
    throw new Error("MODEL_VERSION_HUMAN_ACTOR_REQUIRED");
  }

  const recordedAt =
    at ??
    model.approvedAt ??
    model.updatedAt ??
    new Date().toISOString();
  const id = normalizedRecordId(
    `model-${version}-${normalizedAction}-${recordedAt}`,
    "model",
  );

  const data = cloneJson({
    archiveVersion: LEARNING_CLOUD_ARCHIVE_VERSION,
    archiveType: "MODEL_VERSION_AUDIT",
    id,
    action: normalizedAction,
    version,
    candidateId:
      cleanText(candidateId ?? model.candidateId, 160) || null,
    status: cleanText(model.status, 80) || "RECORDED",
    metrics: model.metrics ?? null,
    weights: model.weights ?? {},
    calibration: model.calibration ?? null,
    rollbackFrom: model.rollbackFrom ?? null,
    approvedBy: actor || null,
    note: cleanText(note ?? model.approvalNote ?? model.rollbackReason, 800) || null,
    recordedAt,
    safety: archiveSafety(),
  });

  return {
    collection: LEARNING_CLOUD_COLLECTIONS.modelVersions,
    id,
    data,
  };
}

export async function saveCandidateArchiveToCloud(
  payload,
  { writer = saveCloudRecord } = {},
) {
  const record = buildCandidateArchiveRecord(payload);
  const response = await writer(record);
  return {
    saved: response?.saved !== false,
    collection: record.collection,
    id: record.id,
    record: record.data,
  };
}

export async function saveForwardValidationArchiveToCloud(
  payload,
  { writer = saveCloudRecord } = {},
) {
  const record = buildForwardValidationArchiveRecord(payload);
  const response = await writer(record);
  return {
    saved: response?.saved !== false,
    collection: record.collection,
    id: record.id,
    record: record.data,
  };
}

export async function saveModelVersionArchiveToCloud(
  payload,
  { writer = saveCloudRecord } = {},
) {
  const record = buildModelVersionArchiveRecord(payload);
  const response = await writer(record);
  return {
    saved: response?.saved !== false,
    collection: record.collection,
    id: record.id,
    record: record.data,
  };
}

function unwrapCloudRecords(payload = {}) {
  return (Array.isArray(payload?.records) ? payload.records : [])
    .map((envelope) => ({
      id: envelope?.id ?? envelope?.data?.id ?? null,
      createdAt: envelope?.createdAt ?? null,
      updatedAt: envelope?.updatedAt ?? null,
      data: envelope?.data ?? null,
    }))
    .filter((entry) => entry.id && entry.data);
}

export async function loadLearningArchiveFromCloud({
  listProvider = listCloudRecords,
  limit = 500,
} = {}) {
  const [candidates, forwardTests, modelVersions] = await Promise.all([
    listProvider({
      collection: LEARNING_CLOUD_COLLECTIONS.candidates,
      limit,
    }),
    listProvider({
      collection: LEARNING_CLOUD_COLLECTIONS.forwardTests,
      limit,
    }),
    listProvider({
      collection: LEARNING_CLOUD_COLLECTIONS.modelVersions,
      limit,
    }),
  ]);

  return {
    version: LEARNING_CLOUD_ARCHIVE_VERSION,
    restoredAt: new Date().toISOString(),
    readOnly: true,
    appliedToRuntime: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    brokerWriteAllowed: false,
    candidates: unwrapCloudRecords(candidates),
    forwardTests: unwrapCloudRecords(forwardTests),
    modelVersions: unwrapCloudRecords(modelVersions),
  };
}

export const LearningCloudRepositoryInternals = Object.freeze({
  MODEL_AUDIT_ACTIONS,
  anyTrue,
  archiveSafety,
  cleanText,
  cloneJson,
  humanApprovalRequired,
  normalizedRecordId,
  requireNoExecutionPermission,
  unwrapCloudRecords,
});
