import { STORAGE_KEYS } from "../config.js";

export const DEFAULT_LEARNING_FEEDBACK_LIMIT = 100;

function validateStorage(storage) {
  if (storage === null || storage === undefined) return null;
  for (const method of ["getItem", "setItem", "removeItem"]) {
    if (typeof storage[method] !== "function") {
      throw new TypeError("Learning feedback storage is invalid.");
    }
  }
  return storage;
}

function restoreReports(values) {
  return (Array.isArray(values) ? values : []).filter(
    (report) =>
      report &&
      typeof report.id === "string" &&
      report.version === "resolved-feedback-v1" &&
      report.executionAllowed === false,
  );
}

function readReports(storage, key) {
  if (!storage) return [];
  try {
    const raw = storage.getItem(key);
    return raw ? restoreReports(JSON.parse(raw)) : [];
  } catch {
    return [];
  }
}

function persistedReport(report) {
  return {
    id: report.id,
    version: report.version,
    generatedAt: report.generatedAt,
    status: report.status,
    weightCandidate: report.weightCandidate,
    marketFeatureCandidate: report.marketFeatureCandidate,
    audit: report.audit,
    executionAllowed: false,
  };
}

export class LearningFeedbackRepository {
  constructor({
    storage = globalThis.localStorage ?? null,
    key = STORAGE_KEYS.learningFeedback,
    limit = DEFAULT_LEARNING_FEEDBACK_LIMIT,
  } = {}) {
    this.storage = validateStorage(storage);
    this.key = key;
    this.limit = Math.max(1, Math.floor(Number(limit) || DEFAULT_LEARNING_FEEDBACK_LIMIT));
    this.reports = readReports(this.storage, this.key).slice(0, this.limit);
  }

  append(report) {
    if (!report?.id || report.executionAllowed !== false) {
      throw new TypeError("Learning feedback report is invalid.");
    }

    const existing = this.reports.find((item) => item.id === report.id);
    if (existing) return { report: existing, inserted: false };

    const stored = persistedReport(report);
    this.reports = [stored, ...this.reports].slice(0, this.limit);
    this.storage?.setItem(this.key, JSON.stringify(this.reports));
    return { report: stored, inserted: true };
  }

  latest() {
    return this.reports[0] ?? null;
  }

  list() {
    return [...this.reports];
  }

  clear() {
    this.storage?.removeItem(this.key);
    this.reports = [];
  }
}

export const LearningFeedbackRepositoryInternals = Object.freeze({
  validateStorage,
  restoreReports,
  readReports,
  persistedReport,
});

export default LearningFeedbackRepository;
