import assert from "node:assert/strict";
import test from "node:test";

import {
  buildRiskAwareDecisionReport,
  evaluateRiskAwareDecision,
} from "../analysis/risk-aware-decision-gate.js";

test(
  "Strong decision within risk limit is approved",
  () => {
    const result =
      evaluateRiskAwareDecision({
        decision: {
          action: "BUY",
          score: 82,
          confidence: 86,
        },

        portfolioRisk: {
          riskPercent: 3,
        },

        limits: {
          maximumRiskPercent: 6,
          minimumConfidence: 55,
          minimumScore: 60,
        },
      });

    assert.equal(
      result.approved,
      true,
    );

    assert.equal(
      result.action,
      "BUY",
    );

    assert.equal(
      result.status,
      "APPROVED",
    );
  },
);

test(
  "Excessive portfolio risk blocks decision",
  () => {
    const result =
      evaluateRiskAwareDecision({
        decision: {
          action: "STRONG BUY",
          score: 92,
          confidence: 90,
        },

        portfolioRisk: {
          riskPercent: 12,
        },

        limits: {
          maximumRiskPercent: 6,
        },
      });

    assert.equal(
      result.approved,
      false,
    );

    assert.ok(
      result.reasons.includes(
        "portfolio_risk_limit_exceeded",
      ),
    );

    assert.ok(
      [
        "WATCH",
        "HOLD",
      ].includes(
        result.action,
      ),
    );
  },
);

test(
  "Low confidence downgrades recommendation",
  () => {
    const result =
      evaluateRiskAwareDecision({
        decision: {
          action: "BUY",
          score: 80,
          confidence: 40,
        },

        portfolioRisk: {
          riskPercent: 2,
        },
      });

    assert.equal(
      result.approved,
      false,
    );

    assert.equal(
      result.action,
      "WATCH",
    );

    assert.ok(
      result.reasons.includes(
        "confidence_below_minimum",
      ),
    );
  },
);

test(
  "Risk-aware report contains summary",
  () => {
    const report =
      buildRiskAwareDecisionReport({
        symbol: "7203.T",

        decision: {
          action: "BUY",
          score: 80,
          confidence: 85,
        },

        portfolioRisk: {
          riskPercent: 3,
        },
      });

    assert.equal(
      report.symbol,
      "7203.T",
    );

    assert.equal(
      report.version,
      "risk-aware-decision-gate-v1",
    );

    assert.ok(
      report.summary.includes(
        "BUY",
      ),
    );
  },
);