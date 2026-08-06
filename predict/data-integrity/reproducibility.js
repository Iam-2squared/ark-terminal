import { DatasetVersionInternals } from "./dataset-version.js";

export const REPRODUCIBILITY_CHECK_VERSION = "reproducibility-check-v1";

export function buildReproducibilityFingerprint({ datasetManifest, modelVersion, config = {}, output = {} } = {}) {
  if (!datasetManifest?.datasetHash) throw new TypeError("datasetManifest.datasetHash is required");
  const canonical = DatasetVersionInternals.stableStringify({
    datasetHash: datasetManifest.datasetHash,
    modelVersion: String(modelVersion ?? "UNKNOWN").trim(),
    config,
    output,
  });
  return {
    version: REPRODUCIBILITY_CHECK_VERSION,
    canonical,
    fingerprint: DatasetVersionInternals.fnv1a(canonical),
  };
}

export function compareReproducibility(first, second) {
  const match = Boolean(first?.fingerprint && first.fingerprint === second?.fingerprint);
  return {
    version: REPRODUCIBILITY_CHECK_VERSION,
    match,
    status: match ? "PASS" : "BLOCKED",
    firstFingerprint: first?.fingerprint ?? null,
    secondFingerprint: second?.fingerprint ?? null,
    safety: {
      executionAllowed: false,
      brokerWriteAllowed: false,
      automaticPromotionAllowed: false,
      productionUpdateAllowed: false,
    },
  };
}

export function assertReproducible(result) {
  if (!result?.match) throw new Error("REPRODUCIBILITY_MISMATCH");
  return true;
}

export default buildReproducibilityFingerprint;
