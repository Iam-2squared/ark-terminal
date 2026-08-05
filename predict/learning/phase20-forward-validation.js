import {
  runWalkForwardAudit,
} from "../analysis/walk-forward-accuracy-audit.js";

import {
  evaluateChampionChallenger,
} from "./champion-challenger-v2.js";

export const PHASE20_FORWARD_VALIDATION_VERSION =
  "phase20-forward-validation-v1";

function cleanText(value, maximumLength = 160) {
  return String(value ?? "").trim().slice(0, maximumLength);
}

function finiteNumber(value, fallback = null) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizeAction(value) {
  const action = String(value ?? "")
    .trim()
    .toUpperCase()
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .replace(/\s+/g, " ");

  if (["BUY", "STRONG BUY", "LONG"].includes(action)) return "BUY";
  if (["SELL", "STRONG SELL", "SHORT", "REDUCE"].includes(action)) {
    return "SELL";
  }
  return "NON_DIRECTIONAL";
}

function predictionKey(prediction = {}) {
  return [
    cleanText(prediction.symbol, 30).toUpperCase(),
    cleanText(prediction.entryDate, 40),
    cleanText(prediction.exitDate, 40),
    finiteNumber(prediction.horizon, 0),
  ].join("|");
}

export function buildPairedForwardRecords({
  championPredictions = [],
  challengerPredictions = [],
} = {}) {
  const championMap = new Map(
    (Array.isArray(championPredictions) ? championPredictions : [])
      .map((prediction) => [predictionKey(prediction), prediction]),
  );
  const challengerMap = new Map(
    (Array.isArray(challengerPredictions) ? challengerPredictions : [])
      .map((prediction) => [predictionKey(prediction), prediction]),
  );

  const allKeys = new Set([...championMap.keys(), ...challengerMap.keys()]);
  const records = [];
  const diagnostics = {
    championPredictions: championMap.size,
    challengerPredictions: challengerMap.size,
    commonSamples: 0,
    pairedDirectionalSamples: 0,
    missingChampion: 0,
    missingChallenger: 0,
    nonDirectionalChampion: 0,
    nonDirectionalChallenger: 0,
    actualReturnMismatch: 0,
  };

  for (const key of [...allKeys].sort()) {
    const champion = championMap.get(key);
    const challenger = challengerMap.get(key);

    if (!champion) {
      diagnostics.missingChampion += 1;
      continue;
    }

    if (!challenger) {
      diagnostics.missingChallenger += 1;
      continue;
    }

    diagnostics.commonSamples += 1;

    const championAction = normalizeAction(champion.action);
    const challengerAction = normalizeAction(challenger.action);

    if (!["BUY", "SELL"].includes(championAction)) {
      diagnostics.nonDirectionalChampion += 1;
      continue;
    }

    if (!["BUY", "SELL"].includes(challengerAction)) {
      diagnostics.nonDirectionalChallenger += 1;
      continue;
    }

    const championActualReturn = finiteNumber(champion.returnPercent);
    const challengerActualReturn = finiteNumber(challenger.returnPercent);

    if (
      championActualReturn === null ||
      challengerActualReturn === null ||
      Math.abs(championActualReturn - challengerActualReturn) > 0.0001
    ) {
      diagnostics.actualReturnMismatch += 1;
      continue;
    }

    records.push({
      id: key,
      timestamp: champion.exitDate,
      symbol: champion.symbol,
      actualReturn: championActualReturn,
      champion: {
        direction: championAction,
        confidence: finiteNumber(champion.confidence, 0),
      },
      challenger: {
        direction: challengerAction,
        confidence: finiteNumber(challenger.confidence, 0),
      },
    });
  }

  diagnostics.pairedDirectionalSamples = records.length;

  return { records, diagnostics };
}

function resolveStatus({ evaluation, validationContext }) {
  if (validationContext?.outOfSample !== true) {
    return "BLOCKED_NOT_OUT_OF_SAMPLE";
  }

  if (validationContext?.paperOnly !== true) {
    return "BLOCKED_NOT_PAPER_ONLY";
  }

  if (evaluation?.decision === "PROMOTE_CHALLENGER") {
    return "READY_FOR_HUMAN_REVIEW";
  }

  if (evaluation?.decision === "REJECT_CHALLENGER") {
    return "REJECTED";
  }

  return "CONTINUE_FORWARD_TEST";
}

export async function runCandidateForwardValidation({
  rows = [],
  championPredictor,
  candidatePredictor,
  championModel = {},
  candidateProposal = {},
  horizon = 5,
  minimumHistory = 20,
  neutralThreshold = 0.5,
  validationContext = {},
  evaluationOptions = {},
  onProgress,
} = {}) {
  if (typeof championPredictor !== "function") {
    throw new TypeError("championPredictor must be a function");
  }

  if (typeof candidatePredictor !== "function") {
    throw new TypeError("candidatePredictor must be a function");
  }

  if (
    !candidateProposal ||
    candidateProposal.status !== "PROPOSED_FOR_VALIDATION" ||
    candidateProposal.safety?.productionUpdateAllowed !== false ||
    candidateProposal.safety?.brokerWriteAllowed !== false
  ) {
    throw new Error("SAFE_CANDIDATE_PROPOSAL_REQUIRED");
  }

  const reportProgress = (stage, payload = {}) => {
    if (typeof onProgress === "function") {
      onProgress({ stage, ...payload });
    }
  };

  reportProgress("CHAMPION_START");
  const championAudit = await runWalkForwardAudit({
    rows,
    predictor: championPredictor,
    horizon,
    minimumHistory,
    neutralThreshold,
    onProgress: (payload) => reportProgress("CHAMPION", payload),
  });

  reportProgress("CHALLENGER_START");
  const challengerAudit = await runWalkForwardAudit({
    rows,
    predictor: candidatePredictor,
    horizon,
    minimumHistory,
    neutralThreshold,
    onProgress: (payload) => reportProgress("CHALLENGER", payload),
  });

  const paired = buildPairedForwardRecords({
    championPredictions: championAudit.predictions,
    challengerPredictions: challengerAudit.predictions,
  });

  const championVersion = cleanText(championModel.version, 100);
  if (!championVersion) throw new Error("CHAMPION_MODEL_VERSION_REQUIRED");

  const challengerVersion =
    cleanText(candidateProposal.candidateVersion, 120) === championVersion
      ? cleanText(candidateProposal.id, 120)
      : cleanText(candidateProposal.candidateVersion ?? candidateProposal.id, 120);

  const evaluation = evaluateChampionChallenger({
    champion: {
      id: cleanText(
        championModel.id ?? championModel.modelId ?? "ark-prediction-model",
        100,
      ),
      version: championVersion,
      family: cleanText(championModel.family ?? "ENSEMBLE", 80),
    },
    challenger: {
      id: cleanText(
        championModel.id ?? championModel.modelId ?? "ark-prediction-model",
        100,
      ),
      version: challengerVersion,
      family: cleanText(championModel.family ?? "ENSEMBLE", 80),
      metadata: {
        proposalId: candidateProposal.id,
      },
    },
    records: paired.records,
    ...evaluationOptions,
    requireHumanApproval: true,
  });

  const safeValidationContext = {
    datasetId: cleanText(validationContext.datasetId, 160) || null,
    datasetWindow: cleanText(validationContext.datasetWindow, 160) || null,
    outOfSample: validationContext.outOfSample === true,
    paperOnly: validationContext.paperOnly === true,
    futureLeakChecked:
      championAudit.futureLeakChecked === true &&
      challengerAudit.futureLeakChecked === true,
    sameSymbolSessionJoin:
      championAudit.crossSymbolJoinBlocked === true &&
      challengerAudit.crossSymbolJoinBlocked === true,
  };

  const status = resolveStatus({
    evaluation,
    validationContext: safeValidationContext,
  });

  const blockers = [...(Array.isArray(evaluation.blockers) ? evaluation.blockers : [])];
  if (!safeValidationContext.outOfSample) blockers.push("OUT_OF_SAMPLE_REQUIRED");
  if (!safeValidationContext.paperOnly) blockers.push("PAPER_ONLY_REQUIRED");
  if (!safeValidationContext.futureLeakChecked) blockers.push("FUTURE_LEAK_CHECK_REQUIRED");
  if (!safeValidationContext.sameSymbolSessionJoin) {
    blockers.push("SAME_SYMBOL_SESSION_JOIN_REQUIRED");
  }

  return {
    version: PHASE20_FORWARD_VALIDATION_VERSION,
    generatedAt: new Date().toISOString(),
    status,
    championModel: evaluation.champion,
    candidate: {
      proposalId: candidateProposal.id,
      version: challengerVersion,
    },
    validationContext: safeValidationContext,
    diagnostics: paired.diagnostics,
    championAudit: {
      version: championAudit.version,
      summary: championAudit.summary,
      diagnostics: championAudit.diagnostics,
    },
    challengerAudit: {
      version: challengerAudit.version,
      summary: challengerAudit.summary,
      diagnostics: challengerAudit.diagnostics,
    },
    evaluation,
    blockers: [...new Set(blockers)],
    safety: {
      paperOnly: true,
      liveBrokerAllowed: false,
      automaticPromotionAllowed: false,
      productionUpdateAllowed: false,
      brokerWriteAllowed: false,
      humanApprovalRequired: true,
      approved: false,
    },
  };
}

export function recordCandidateForwardValidation({
  result,
  orchestrator,
  candidateId,
} = {}) {
  if (!result || result.version !== PHASE20_FORWARD_VALIDATION_VERSION) {
    throw new Error("VALID_FORWARD_VALIDATION_RESULT_REQUIRED");
  }

  if (typeof orchestrator?.recordWalkForward !== "function") {
    throw new TypeError("orchestrator.recordWalkForward is required");
  }

  const challenger = result.evaluation?.challenger ?? {};

  return orchestrator.recordWalkForward(candidateId, {
    metrics: {
      accuracy: finiteNumber(challenger.accuracy),
      winRate: finiteNumber(challenger.accuracy),
      profitFactor: finiteNumber(challenger.profitFactor),
      maxDrawdown: finiteNumber(challenger.maximumDrawdown),
      averageReturn: finiteNumber(challenger.averageReturn),
    },
    outOfSample: result.validationContext?.outOfSample === true,
    futureLeakChecked: result.validationContext?.futureLeakChecked === true,
    passed: result.status === "READY_FOR_HUMAN_REVIEW",
  });
}

export const Phase20ForwardValidationInternals = {
  finiteNumber,
  normalizeAction,
  predictionKey,
  resolveStatus,
};
