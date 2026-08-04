export const EXECUTION_LEARNING_PIPELINE_V1_VERSION =
  "execution-learning-pipeline-v1";

function clone(value) {
  return value === undefined ? undefined : structuredClone(value);
}

function closedExecutionRecords(records = []) {
  return (Array.isArray(records) ? records : []).filter((record) => {
    const action = String(record?.action ?? "").toUpperCase();
    const status = String(record?.status ?? record?.outcome ?? "").toUpperCase();
    return ["BUY", "SELL"].includes(action) && ["WIN", "LOSS", "FLAT", "CLOSED"].includes(status);
  });
}

export class ExecutionLearningPipelineV1 {
  constructor({
    candidateBuilder,
    walkForwardEvaluator,
    productionModel = null,
  } = {}) {
    if (typeof candidateBuilder !== "function") {
      throw new TypeError("candidateBuilder is required.");
    }
    if (typeof walkForwardEvaluator !== "function") {
      throw new TypeError("walkForwardEvaluator is required.");
    }

    this.candidateBuilder = candidateBuilder;
    this.walkForwardEvaluator = walkForwardEvaluator;
    this.productionModel = clone(productionModel);
    this.candidates = new Map();
    this.audit = [];
  }

  createCandidate({ records = [], metadata = {} } = {}) {
    const dataset = closedExecutionRecords(records);
    if (dataset.length === 0) {
      throw new Error("No closed execution-derived trades are available for learning.");
    }

    const candidate = this.candidateBuilder({
      records: clone(dataset),
      metadata: clone(metadata),
      productionModel: clone(this.productionModel),
    });

    if (!candidate?.id) {
      throw new Error("Candidate builder must return an id.");
    }

    const stored = {
      ...clone(candidate),
      status: "CANDIDATE",
      datasetSize: dataset.length,
      createdAt: new Date().toISOString(),
      walkForward: null,
      approvedAt: null,
    };

    this.candidates.set(stored.id, stored);
    this.#record("CANDIDATE_CREATED", { candidateId: stored.id, datasetSize: dataset.length });
    return clone(stored);
  }

  evaluateCandidate(candidateId) {
    const candidate = this.#get(candidateId);
    const evaluation = this.walkForwardEvaluator({
      candidate: clone(candidate),
      productionModel: clone(this.productionModel),
    });

    candidate.walkForward = clone(evaluation);
    candidate.status = evaluation?.passed === true ? "AWAITING_APPROVAL" : "REJECTED";
    this.#record("WALK_FORWARD_COMPLETED", {
      candidateId,
      passed: evaluation?.passed === true,
    });
    return clone(candidate);
  }

  approveCandidate(candidateId, { approvedBy } = {}) {
    const candidate = this.#get(candidateId);
    if (candidate.status !== "AWAITING_APPROVAL") {
      throw new Error("Candidate must pass walk-forward before approval.");
    }
    if (!approvedBy) {
      throw new Error("Human approver identity is required.");
    }

    candidate.status = "APPROVED";
    candidate.approvedAt = new Date().toISOString();
    candidate.approvedBy = String(approvedBy);
    this.#record("CANDIDATE_APPROVED", { candidateId, approvedBy: candidate.approvedBy });
    return clone(candidate);
  }

  promoteApprovedCandidate(candidateId) {
    const candidate = this.#get(candidateId);
    if (candidate.status !== "APPROVED") {
      throw new Error("Only a human-approved candidate can be promoted.");
    }

    this.productionModel = {
      ...clone(candidate.model ?? candidate),
      promotedFromCandidateId: candidate.id,
      promotedAt: new Date().toISOString(),
    };
    candidate.status = "PRODUCTION";
    this.#record("PRODUCTION_PROMOTED", { candidateId });
    return clone(this.productionModel);
  }

  getState() {
    return {
      version: EXECUTION_LEARNING_PIPELINE_V1_VERSION,
      productionModel: clone(this.productionModel),
      candidates: clone(Array.from(this.candidates.values())),
      audit: clone(this.audit),
      autoPromotionAllowed: false,
    };
  }

  #get(id) {
    const candidate = this.candidates.get(id);
    if (!candidate) throw new Error(`Candidate not found: ${id}`);
    return candidate;
  }

  #record(type, data) {
    this.audit.push({ type, data: clone(data), timestamp: new Date().toISOString() });
  }
}

export default ExecutionLearningPipelineV1;
