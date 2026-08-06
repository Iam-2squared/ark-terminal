import { auditPhase48Payload } from "./phase48-evaluation-payload.js";

const pct = (value) => `${(Number(value || 0) * 100).toFixed(1)}%`;
const num = (value, digits = 2) => Number(value || 0).toFixed(digits);

export function buildPhase48DashboardView(payload) {
  const audit = auditPhase48Payload(payload);
  if (audit.status !== "VALID") {
    return Object.freeze({ status: "BLOCKED", blockers: audit.blockers, cards: Object.freeze([]) });
  }

  return Object.freeze({
    status: "READY_FOR_UI",
    modelHealth: payload.modelHealth,
    headline: Object.freeze({
      aiScore: num(payload.prediction.aiScore, 1),
      expectedReturn: pct(payload.prediction.expectedReturn),
      confidence: pct(payload.prediction.confidence),
      adoptedModel: payload.model.type,
    }),
    periods: Object.freeze({
      training: payload.model.trainingPeriod,
      test: payload.model.testPeriod,
      walkForwardFolds: payload.model.walkForwardFolds,
    }),
    cards: Object.freeze([
      { key: "accuracy", label: "Accuracy", value: pct(payload.metrics.accuracy) },
      { key: "auc", label: "AUC", value: num(payload.metrics.auc, 3) },
      { key: "profitFactor", label: "Profit Factor", value: num(payload.metrics.profitFactor, 2) },
      { key: "sharpe", label: "Sharpe", value: num(payload.metrics.sharpe, 2) },
      { key: "maximumDrawdown", label: "Max DD", value: pct(payload.metrics.maximumDrawdown) },
      { key: "tradeCount", label: "Trade Count", value: String(payload.metrics.tradeCount) },
    ]),
    reasons: payload.majorReasons,
    risks: payload.majorRisks,
    sampleCount: payload.audit.sampleCount,
    reviewRequired: true,
    safety: payload.safety,
  });
}
