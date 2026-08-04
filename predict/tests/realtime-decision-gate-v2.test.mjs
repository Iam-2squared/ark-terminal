import test from "node:test";
import assert from "node:assert/strict";

import {
  RealtimeDecisionGateV2,
  evaluateRealtimeDecisionGate,
} from "../realtime/realtime-decision-gate-v2.js";

function healthyInput() {
  return {
    signal: {
      symbol:
        "285A",

      direction:
        "BUY",

      confidence:
        82,

      score:
        84,

      riskScore:
        25,

      freshness:
        "FRESH",

      tradable:
        true,
    },

    marketContext: {
      ready:
        true,

      score:
        75,

      regime:
        "RISK_ON",

      recommendation: {
        action:
          "ALLOW_LONG_BIAS",

        riskMultiplier:
          1,
      },

      diagnostics: {
        stale:
          false,
      },

      freshness: {
        staleSourceCount:
          0,
      },
    },

    anomaly: {
      ready:
        true,

      anomalyDetected:
        false,

      severity:
        "LOW",

      anomalyScore:
        0,

      recommendation: {
        action:
          "CONTINUE",

        tradable:
          true,
      },
    },

    portfolio: {
      exposurePercent:
        35,

      dailyLossPercent:
        0.5,

      openPositions:
        3,

      symbolExposurePercent:
        10,

      availableCashPercent:
        65,
    },
  };
}

test(
  "Realtime decision gate allows healthy trade",
  () => {
    const result =
      evaluateRealtimeDecisionGate(
        healthyInput(),
      );

    assert.equal(
      result.version,
      "realtime-decision-gate-v2",
    );

    assert.equal(
      result.decision,
      "ALLOW",
    );

    assert.equal(
      result.tradable,
      true,
    );

    assert.equal(
      result.executionPlan
        .allowed,
      true,
    );

    assert.ok(
      result.positionMultiplier >
      0,
    );
  },
);

test(
  "Realtime decision gate blocks stale signal",
  () => {
    const input =
      healthyInput();

    input.signal.freshness =
      "STALE";

    const result =
      evaluateRealtimeDecisionGate(
        input,
      );

    assert.equal(
      result.decision,
      "WAIT",
    );

    assert.equal(
      result.tradable,
      false,
    );

    assert.ok(
      result.blockers.includes(
        "SIGNAL_FRESHNESS",
      ),
    );
  },
);

test(
  "Realtime decision gate blocks critical anomaly",
  () => {
    const input =
      healthyInput();

    input.anomaly = {
      ready:
        true,

      anomalyDetected:
        true,

      severity:
        "CRITICAL",

      anomalyScore:
        95,

      recommendation: {
        action:
          "BLOCK",

        tradable:
          false,
      },
    };

    const result =
      evaluateRealtimeDecisionGate(
        input,
      );

    assert.equal(
      result.decision,
      "BLOCK",
    );

    assert.equal(
      result.positionMultiplier,
      0,
    );

    assert.ok(
      result.blockers.includes(
        "REALTIME_ANOMALY_GATE",
      ),
    );
  },
);

test(
  "Realtime decision gate blocks daily loss limit",
  () => {
    const input =
      healthyInput();

    input.portfolio.dailyLossPercent =
      5;

    const result =
      evaluateRealtimeDecisionGate({
        ...input,

        maximumDailyLoss:
          3,
      });

    assert.equal(
      result.decision,
      "BLOCK",
    );

    assert.ok(
      result.blockers.includes(
        "DAILY_LOSS_LIMIT",
      ),
    );
  },
);

test(
  "Realtime decision gate waits on low confidence",
  () => {
    const input =
      healthyInput();

    input.signal.confidence =
      40;

    const result =
      evaluateRealtimeDecisionGate({
        ...input,

        minimumConfidence:
          60,

        minimumGateScore:
          95,
      });

    assert.equal(
      result.decision,
      "WAIT",
    );

    assert.ok(
      result.blockers.includes(
        "MINIMUM_CONFIDENCE",
      ),
    );
  },
);

test(
  "Realtime decision gate blocks excessive signal risk",
  () => {
    const input =
      healthyInput();

    input.signal.riskScore =
      90;

    const result =
      evaluateRealtimeDecisionGate({
        ...input,

        maximumSignalRisk:
          70,
      });

    assert.equal(
      result.decision,
      "BLOCK",
    );

    assert.ok(
      result.blockers.includes(
        "SIGNAL_RISK_LIMIT",
      ),
    );
  },
);

test(
  "Realtime decision gate blocks stale market context",
  () => {
    const input =
      healthyInput();

    input.marketContext
      .diagnostics
      .stale =
      true;

    const result =
      evaluateRealtimeDecisionGate(
        input,
      );

    assert.equal(
      result.decision,
      "WAIT",
    );

    assert.ok(
      result.blockers.includes(
        "MARKET_CONTEXT_FRESH",
      ),
    );
  },
);

test(
  "Realtime decision gate blocks portfolio exposure",
  () => {
    const input =
      healthyInput();

    input.portfolio
      .exposurePercent =
      95;

    const result =
      evaluateRealtimeDecisionGate({
        ...input,

        maximumPortfolioExposure:
          80,
      });

    assert.equal(
      result.decision,
      "WAIT",
    );

    assert.ok(
      result.blockers.includes(
        "PORTFOLIO_EXPOSURE",
      ),
    );
  },
);

test(
  "Realtime decision gate rejects neutral direction",
  () => {
    const input =
      healthyInput();

    input.signal.direction =
      "NEUTRAL";

    const result =
      evaluateRealtimeDecisionGate(
        input,
      );

    assert.equal(
      result.tradable,
      false,
    );

    assert.ok(
      result.blockers.includes(
        "DIRECTIONAL_SIGNAL",
      ),
    );
  },
);

test(
  "Realtime decision gate class is deterministic",
  () => {
    const engine =
      new RealtimeDecisionGateV2({
        minimumGateScore:
          80,
      });

    const first =
      engine.evaluate(
        healthyInput(),
      );

    const second =
      engine.evaluate(
        healthyInput(),
      );

    assert.equal(
      first.decision,
      second.decision,
    );

    assert.equal(
      first.gateScore,
      second.gateScore,
    );

    assert.deepEqual(
      first.blockers,
      second.blockers,
    );
  },
);