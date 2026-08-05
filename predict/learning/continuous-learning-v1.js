export const CONTINUOUS_LEARNING_V1_VERSION = "continuous-learning-v1";

function finiteNumber(value, fallback = null) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function normalizeMetrics(metrics = {}) {
  return {
    accuracy: finiteNumber(metrics.accuracy ?? metrics.predictionAccuracy),
    winRate: finiteNumber(metrics.winRate ?? metrics.tradeWinRate),
    profitFactor: finiteNumber(metrics.profitFactor ?? metrics.pf),
    sharpe: finiteNumber(metrics.sharpe ?? metrics.sharpeRatio),
    maxDrawdown: finiteNumber(metrics.maxDrawdown ?? metrics.dd),
    averageReturn: finiteNumber(metrics.averageReturn ?? metrics.averageReturnPercent),
  };
}

function compareMetrics(candidate, production) {
  const deltas = {
    accuracy: (candidate.accuracy ?? 0) - (production.accuracy ?? 0),
    winRate: (candidate.winRate ?? 0) - (production.winRate ?? 0),
    profitFactor: (candidate.profitFactor ?? 0) - (production.profitFactor ?? 0),
    sharpe: (candidate.sharpe ?? 0) - (production.sharpe ?? 0),
    maxDrawdown: (production.maxDrawdown ?? 0) - (candidate.maxDrawdown ?? 0),
    averageReturn: (candidate.averageReturn ?? 0) - (production.averageReturn ?? 0),
  };
  const improved =
    deltas.profitFactor > 0 &&
    deltas.sharpe >= 0 &&
    deltas.maxDrawdown >= 0 &&
    deltas.averageReturn >= 0;
  return { deltas, improved };
}

function defaultId(prefix = "candidate") {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export class ContinuousLearningOrchestratorV1 {
  constructor({ storage = null, storageKey = "ark.continuous-learning.v1", maxHistory = 100 } = {}) {
    this.storage = storage;
    this.storageKey = storageKey;
    this.maxHistory = Math.max(1, Number(maxHistory) || 100);
    this.state = this.#load();
  }

  #load() {
    try {
      const raw = this.storage?.getItem?.(this.storageKey);
      if (!raw) return { production: null, candidates: [], history: [] };
      const parsed = JSON.parse(raw);
      return {
        production: parsed?.production ?? null,
        candidates: Array.isArray(parsed?.candidates) ? parsed.candidates : [],
        history: Array.isArray(parsed?.history) ? parsed.history : [],
      };
    } catch {
      return { production: null, candidates: [], history: [] };
    }
  }

  #save() {
    this.state.history = this.state.history.slice(-this.maxHistory);
    this.storage?.setItem?.(this.storageKey, JSON.stringify(this.state));
  }

  setProduction(model) {
    if (!model?.version) throw new Error("PRODUCTION_VERSION_REQUIRED");
    this.state.production = {
      ...model,
      metrics: normalizeMetrics(model.metrics),
      status: "PRODUCTION",
      productionUpdateAllowed: false,
      updatedAt: new Date().toISOString(),
    };
    this.#save();
    return this.state.production;
  }

  createCandidate({ sourceTradeCount = 0, weights = {}, calibration = null, drift = null, metadata = {} } = {}) {
    const candidate = {
      id: defaultId(),
      version: metadata.version ?? `candidate-${Date.now()}`,
      createdAt: new Date().toISOString(),
      sourceTradeCount: Number(sourceTradeCount) || 0,
      weights,
      calibration,
      drift,
      metadata,
      status: "CANDIDATE",
      walkForward: null,
      comparison: null,
      humanApprovalRequired: true,
      productionUpdateAllowed: false,
    };
    this.state.candidates.push(candidate);
    this.state.history.push({ type: "CANDIDATE_CREATED", candidateId: candidate.id, at: candidate.createdAt });
    this.#save();
    return candidate;
  }

  recordWalkForward(candidateId, result = {}) {
    const candidate = this.getCandidate(candidateId);
    if (!candidate) throw new Error("CANDIDATE_NOT_FOUND");
    candidate.walkForward = {
      metrics: normalizeMetrics(result.metrics ?? result),
      outOfSample: result.outOfSample === true,
      futureLeakChecked: result.futureLeakChecked === true,
      passed: result.passed === true,
      completedAt: new Date().toISOString(),
    };
    candidate.status = candidate.walkForward.passed ? "VALIDATED" : "REJECTED";
    this.state.history.push({ type: "WALK_FORWARD_RECORDED", candidateId, passed: candidate.walkForward.passed, at: candidate.walkForward.completedAt });
    this.#save();
    return candidate;
  }

  compareToProduction(candidateId) {
    const candidate = this.getCandidate(candidateId);
    if (!candidate) throw new Error("CANDIDATE_NOT_FOUND");
    if (!candidate.walkForward?.passed || !candidate.walkForward.outOfSample || !candidate.walkForward.futureLeakChecked) {
      candidate.status = "REJECTED";
      candidate.comparison = { readyForReview: false, reason: "VALIDATION_REQUIREMENTS_NOT_MET" };
      this.#save();
      return candidate.comparison;
    }
    if (!this.state.production) {
      candidate.comparison = { readyForReview: true, reason: "NO_PRODUCTION_MODEL", deltas: null };
      candidate.status = "READY_FOR_REVIEW";
      this.#save();
      return candidate.comparison;
    }
    const productionMetrics = normalizeMetrics(this.state.production.metrics);
    const candidateMetrics = normalizeMetrics(candidate.walkForward.metrics);
    const comparison = compareMetrics(candidateMetrics, productionMetrics);
    candidate.comparison = {
      ...comparison,
      readyForReview: comparison.improved,
      comparedAt: new Date().toISOString(),
    };
    candidate.status = comparison.improved ? "READY_FOR_REVIEW" : "REJECTED";
    this.#save();
    return candidate.comparison;
  }

  approveCandidate(candidateId, { approvedBy, note = null } = {}) {
    const candidate = this.getCandidate(candidateId);
    if (!candidate) throw new Error("CANDIDATE_NOT_FOUND");
    if (candidate.status !== "READY_FOR_REVIEW") throw new Error("CANDIDATE_NOT_READY_FOR_REVIEW");
    if (!approvedBy) throw new Error("HUMAN_APPROVAL_REQUIRED");
    const previous = this.state.production;
    this.state.production = {
      version: candidate.version,
      candidateId: candidate.id,
      metrics: normalizeMetrics(candidate.walkForward?.metrics),
      weights: candidate.weights,
      calibration: candidate.calibration,
      approvedBy,
      approvalNote: note,
      approvedAt: new Date().toISOString(),
      rollbackFrom: previous?.version ?? null,
      status: "PRODUCTION",
      productionUpdateAllowed: false,
    };
    candidate.status = "APPROVED";
    candidate.approvedBy = approvedBy;
    candidate.approvedAt = this.state.production.approvedAt;
    this.state.history.push({ type: "CANDIDATE_APPROVED", candidateId, approvedBy, previousProductionVersion: previous?.version ?? null, at: candidate.approvedAt });
    this.#save();
    return this.state.production;
  }

  rollback(targetVersion, { approvedBy, reason = null } = {}) {
    if (!approvedBy) throw new Error("HUMAN_APPROVAL_REQUIRED");
    const source = this.state.candidates.find((item) => item.version === targetVersion && item.status === "APPROVED");
    if (!source) throw new Error("ROLLBACK_TARGET_NOT_FOUND");
    const previous = this.state.production;
    this.state.production = {
      version: source.version,
      candidateId: source.id,
      metrics: normalizeMetrics(source.walkForward?.metrics),
      weights: source.weights,
      calibration: source.calibration,
      approvedBy,
      approvedAt: new Date().toISOString(),
      rollbackFrom: previous?.version ?? null,
      rollbackReason: reason,
      status: "PRODUCTION",
      productionUpdateAllowed: false,
    };
    this.state.history.push({ type: "ROLLBACK", targetVersion, approvedBy, previousProductionVersion: previous?.version ?? null, reason, at: this.state.production.approvedAt });
    this.#save();
    return this.state.production;
  }

  getCandidate(candidateId) {
    return this.state.candidates.find((item) => item.id === candidateId) ?? null;
  }

  getState() {
    return JSON.parse(JSON.stringify({ ...this.state, version: CONTINUOUS_LEARNING_V1_VERSION }));
  }
}

export default ContinuousLearningOrchestratorV1;
