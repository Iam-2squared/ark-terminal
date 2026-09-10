import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';

export const ALLOWED_SESSIONS = Object.freeze([
  '2025-08-27',
  '2025-10-09',
  '2025-11-25',
]);

export const SAFETY = Object.freeze({
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  transmitted: false,
});

export const DENIED_FIELD_PATTERNS = Object.freeze([
  /^future/i,
  /label/i,
  /outcome/i,
  /^mfe/i,
  /^mae/i,
  /^exit/i,
  /^profit/i,
  /^win(?:Rate|ner)?$/i,
  /^loss$/i,
  /^returnAfter/i,
  /^target/i,
]);

const datePattern = /^\d{4}-\d{2}-\d{2}$/;

export function assertAllowedSession(sessionDate) {
  assert.equal(typeof sessionDate, 'string', 'SESSION_DATE_REQUIRED');
  assert.match(sessionDate, datePattern, 'INVALID_SESSION_DATE');
  assert(ALLOWED_SESSIONS.includes(sessionDate), `UNAPPROVED_SESSION:${sessionDate}`);
  return sessionDate;
}

export function assertSourceLineage(lineage) {
  assert(lineage && typeof lineage === 'object', 'SOURCE_LINEAGE_REQUIRED');
  assert(Number.isInteger(lineage.runId) && lineage.runId > 0, 'SOURCE_RUN_ID_REQUIRED');
  assert(Number.isInteger(lineage.artifactId) && lineage.artifactId > 0, 'SOURCE_ARTIFACT_ID_REQUIRED');
  assert.equal(typeof lineage.artifactName, 'string', 'SOURCE_ARTIFACT_NAME_REQUIRED');
  assert.match(lineage.digest ?? '', /^sha256:[0-9a-f]{64}$/, 'SOURCE_DIGEST_REQUIRED');
  return true;
}

export function fieldIsDenied(field) {
  return DENIED_FIELD_PATTERNS.some((pattern) => pattern.test(field));
}

export function stripOutcomeFields(value) {
  if (Array.isArray(value)) return value.map(stripOutcomeFields);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(Object.entries(value)
    .filter(([key]) => !fieldIsDenied(key))
    .map(([key, child]) => [key, stripOutcomeFields(child)]));
}

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(Object.keys(value).sort().map((key) => [key, canonicalize(value[key])]));
}

export function deterministicSubsetSha256(value) {
  return createHash('sha256').update(JSON.stringify(canonicalize(value))).digest('hex');
}

export function validateExtractionRequest(request) {
  assert(request && typeof request === 'object', 'EXTRACTION_REQUEST_REQUIRED');
  assertAllowedSession(request.sessionDate);
  assertSourceLineage(request.lineage);
  assert.equal(request.readOnly, true, 'EXTRACTOR_MUST_BE_READ_ONLY');
  assert.equal(request.materializesFullArtifact, false, 'FULL_ARTIFACT_MATERIALIZATION_FORBIDDEN');
  assert.equal(request.transport, 'SERVER_SIDE_MEMBER_FILTER', 'SERVER_SIDE_MEMBER_FILTER_REQUIRED');
  assert.equal(request.providerSupportsMemberFilter, true, 'PROVIDER_MEMBER_FILTER_NOT_SUPPORTED');
  assert.equal(request.invokesExit, false, 'EXIT_INVOCATION_FORBIDDEN');
  assert.equal(request.accessesProtectedOrFresh, false, 'PROTECTED_OR_FRESH_ACCESS_FORBIDDEN');
  return true;
}

export function evaluateGithubArtifactApi(capabilities) {
  const memberFilter = capabilities?.serverSideMemberFilter === true;
  const memberListing = capabilities?.serverSideMemberListing === true;
  const wholeZipOnly = capabilities?.downloadUnit === 'ZIP_ARCHIVE';
  return Object.freeze({
    status: memberFilter && memberListing && !wholeZipOnly
      ? 'SUPPORTED'
      : 'READ_ONLY_EXTRACTION_NOT_SUPPORTED',
    serverSideMemberFilter: memberFilter,
    serverSideMemberListing: memberListing,
    fullArtifactDownloadRequired: !memberFilter || wholeZipOnly,
    extractionExecuted: false,
  });
}
