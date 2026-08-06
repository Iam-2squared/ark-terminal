export const DATASET_VERSION_MANIFEST_VERSION = "dataset-version-manifest-v1";

function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stableValue(value[key])]));
  }
  return value;
}

function stableStringify(value) {
  return JSON.stringify(stableValue(value));
}

function fnv1a(input) {
  let hash = 0x811c9dc5;
  for (let index = 0; index < input.length; index += 1) {
    hash ^= input.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export function buildDatasetVersionManifest({
  datasetId,
  generatedAt,
  period = {},
  symbols = [],
  featureVersion,
  labelVersion,
  sourceVersion,
  metadata = {},
} = {}) {
  const normalized = {
    version: DATASET_VERSION_MANIFEST_VERSION,
    datasetId: String(datasetId ?? "").trim(),
    generatedAt: new Date(generatedAt ?? Date.now()).toISOString(),
    period: {
      from: period.from ? new Date(period.from).toISOString() : null,
      to: period.to ? new Date(period.to).toISOString() : null,
    },
    symbols: [...new Set((Array.isArray(symbols) ? symbols : []).map((symbol) => String(symbol).trim().toUpperCase()).filter(Boolean))].sort(),
    featureVersion: String(featureVersion ?? "UNKNOWN").trim(),
    labelVersion: String(labelVersion ?? "UNKNOWN").trim(),
    sourceVersion: String(sourceVersion ?? "UNKNOWN").trim(),
    metadata: stableValue(metadata),
  };

  if (!normalized.datasetId) throw new TypeError("datasetId is required");
  if (!normalized.period.from || !normalized.period.to) throw new TypeError("period.from and period.to are required");

  const canonical = stableStringify(normalized);
  return {
    ...normalized,
    hashAlgorithm: "FNV1A32",
    datasetHash: fnv1a(canonical),
    canonical,
    safety: {
      executionAllowed: false,
      brokerWriteAllowed: false,
      productionUpdateAllowed: false,
    },
  };
}

export const DatasetVersionInternals = Object.freeze({ stableValue, stableStringify, fnv1a });
export default buildDatasetVersionManifest;
