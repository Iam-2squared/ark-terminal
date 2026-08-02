import {
  executeAIPipeline,
} from "./ai-pipeline.js";

function finiteNumber(
  value,
  fallback = 0,
) {
  const parsed =
    Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : fallback;
}

function normalizeArray(value) {
  return Array.isArray(value)
    ? value
    : [];
}

export function composeAIResult(
  pipeline = {},
) {
  const runtime =
    pipeline.runtime ??
    pipeline.coordinator?.runtime ??
    pipeline.bootstrap?.runtime ??
    {};

  const dashboard =
    runtime.dashboard ??
    {};

  const consensus =
    runtime.consensus ??
    {};

  const tradePlan =
    runtime.tradePlan ??
    {};

  const gatedDecision =
    runtime.gatedDecision ??
    {};

  const marketIntelligence =
    runtime.marketIntelligence ??
    null;

  return {
    version:
      "ai-result-composer-v1",

    generatedAt:
      runtime.generatedAt ??
      new Date().toISOString(),

    symbol:
      runtime.normalized?.symbol ??
      null,

    status:
      runtime.status ??
      "unknown",

    action:
      tradePlan.action ??
      gatedDecision.action ??
      consensus.action ??
      dashboard.action ??
      "HOLD",

    score:
      finiteNumber(
        consensus.score ??
        gatedDecision.score ??
        dashboard.score,
        50,
      ),

    confidence:
      finiteNumber(
        runtime.calibratedConfidence
          ?.confidence ??
        gatedDecision.confidence ??
        dashboard.confidence,
        0,
      ),

    agreementRate:
      finiteNumber(
        consensus.agreementRate,
        0,
      ),

    approved:
      gatedDecision.approved === true,

    executable:
      tradePlan.executable === true,

    shares:
      finiteNumber(
        tradePlan.sizing?.shares,
        0,
      ),

    entryPrice:
      finiteNumber(
        tradePlan.levels?.entryPrice,
        0,
      ),

    stopPrice:
      finiteNumber(
        tradePlan.levels?.stopPrice,
        0,
      ),

    targetPrice:
      finiteNumber(
        tradePlan.levels?.targetPrice,
        0,
      ),

    estimatedCost:
      finiteNumber(
        tradePlan.sizing
          ?.estimatedCost,
        0,
      ),

    buyFactors:
      normalizeArray(
        dashboard.buyFactors ??
        runtime.analysis
          ?.decision
          ?.buyFactors,
      ),

    riskFactors:
      normalizeArray(
        dashboard.riskFactors ??
        runtime.analysis
          ?.decision
          ?.riskFactors ??
        gatedDecision.reasons,
      ),

    marketIntelligence,

    raw: {
      consensus,
      gatedDecision,
      tradePlan,
      marketIntelligence,
    },
  };
}

export async function runAIAnalysis(
  input = {},
) {
  const pipeline =
    await executeAIPipeline(
      input,
    );

  return composeAIResult(
    pipeline,
  );
}
