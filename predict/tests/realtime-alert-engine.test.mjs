import assert from "node:assert/strict";
import test from "node:test";

import {
  acknowledgeRealtimeAlert,
  appendRealtimeAlert,
  createRealtimeAlert,
  evaluateRealtimeAlert,
  RealtimeAlertEngine,
  summarizeRealtimeAlerts,
} from "../analysis/realtime-alert-engine.js";

test(
  "Strong buy condition triggers alert",
  () => {
    const result =
      evaluateRealtimeAlert({
        symbol: "7203.T",

        current: {
          action:
            "STRONG BUY",

          score:
            90,

          confidence:
            88,

          riskPercent:
            3,
        },

        previous: {
          action:
            "BUY",

          score:
            80,
        },
      });

    assert.equal(
      result.triggered,
      true,
    );

    assert.equal(
      result.severity,
      "HIGH",
    );

    assert.ok(
      result.reasons.includes(
        "buy_conditions_met",
      ),
    );
  },
);

test(
  "Risk limit breach triggers high severity alert",
  () => {
    const result =
      evaluateRealtimeAlert({
        symbol: "AAA",

        current: {
          action:
            "HOLD",

          score:
            60,

          confidence:
            50,

          riskPercent:
            12,
        },

        thresholds: {
          maximumRiskPercent:
            6,
        },
      });

    assert.equal(
      result.triggered,
      true,
    );

    assert.equal(
      result.severity,
      "HIGH",
    );

    assert.ok(
      result.reasons.includes(
        "risk_limit_exceeded",
      ),
    );
  },
);

test(
  "No meaningful change produces no alert",
  () => {
    const result =
      evaluateRealtimeAlert({
        symbol: "AAA",

        current: {
          action:
            "HOLD",

          score:
            50,

          confidence:
            50,

          riskPercent:
            2,
        },

        previous: {
          action:
            "HOLD",

          score:
            49,
        },
      });

    assert.equal(
      result.triggered,
      false,
    );

    assert.equal(
      createRealtimeAlert(
        result,
      ),
      null,
    );
  },
);

test(
  "Alert history and acknowledgement work",
  () => {
    const alert =
      createRealtimeAlert({
        triggered:
          true,

        severity:
          "MEDIUM",

        symbol:
          "AAA",

        action:
          "BUY",

        score:
          80,

        confidence:
          75,

        riskPercent:
          2,

        reasons: [
          "buy_conditions_met",
        ],

        message:
          "AAA BUY",
      });

    const alerts =
      appendRealtimeAlert({
        alerts: [],
        alert,
      });

    const acknowledged =
      acknowledgeRealtimeAlert({
        alerts,

        alertId:
          alert.id,
      });

    assert.equal(
      acknowledged[0]
        .acknowledged,
      true,
    );

    const summary =
      summarizeRealtimeAlerts(
        acknowledged,
      );

    assert.equal(
      summary.total,
      1,
    );

    assert.equal(
      summary.unread,
      0,
    );
  },
);

test(
  "Realtime engine tracks previous state",
  () => {
    const engine =
      new RealtimeAlertEngine({
        thresholds: {
          minimumScoreChange:
            5,
        },
      });

    engine.update({
      symbol:
        "AAA",

      current: {
        action:
          "HOLD",

        score:
          50,

        confidence:
          50,

        riskPercent:
          2,
      },
    });

    const result =
      engine.update({
        symbol:
          "AAA",

        current: {
          action:
            "BUY",

          score:
            80,

          confidence:
            80,

          riskPercent:
            2,
        },
      });

    assert.equal(
      result.evaluation
        .triggered,
      true,
    );

    assert.ok(
      result.alert,
    );

    assert.equal(
      result.summary.total,
      1,
    );
  },
);