import assert from "node:assert/strict";
import test from "node:test";

import {
  buildRuntimeDiagnosticReport,
  inspectRuntimePayload,
  renderRuntimeDiagnosticBadge,
  verifyRuntimeModules,
} from "../analysis/runtime-diagnostics.js";

function healthyRuntime() {
  return {
    status: "ready",

    html:
      "<section>AI Analysis</section>",

    analysis: {
      dashboard: {
        action: "BUY",
        score: 82,
        confidence: 88,
        macro: "BULLISH",
        regime: "BULL",
      },

      decision: {
        buyFactors: [
          "Strong trend",
        ],

        riskFactors: [
          "Volatility",
        ],
      },
    },
  };
}

test(
  "Healthy runtime payload passes diagnostics",
  () => {
    const result =
      inspectRuntimePayload(
        healthyRuntime(),
      );

    assert.equal(
      result.healthy,
      true,
    );

    assert.equal(
      result.score,
      100,
    );

    assert.equal(
      result.grade,
      "A",
    );
  },
);

test(
  "Missing runtime data fails diagnostics",
  () => {
    const result =
      inspectRuntimePayload({});

    assert.equal(
      result.healthy,
      false,
    );

    assert.ok(
      result.issues.length > 0,
    );
  },
);

test(
  "Runtime module verification reports failures",
  async () => {
    const result =
      await verifyRuntimeModules({
        modules: [
          "good",
          "bad",
        ],

        importer:
          async (path) => {
            if (path === "bad") {
              throw new Error(
                "module failure",
              );
            }

            return {
              example: true,
            };
          },
      });

    assert.equal(
      result.healthy,
      false,
    );

    assert.equal(
      result.loadedCount,
      1,
    );

    assert.equal(
      result.failedCount,
      1,
    );
  },
);

test(
  "Diagnostic report combines payload and module health",
  () => {
    const result =
      buildRuntimeDiagnosticReport({
        runtime:
          healthyRuntime(),

        modules: {
          healthy: true,
          checkedCount: 7,
          loadedCount: 7,
          failedCount: 0,
          results: [],
        },
      });

    assert.equal(
      result.healthy,
      true,
    );

    assert.equal(
      result.summary,
      "AI runtime is healthy.",
    );
  },
);

test(
  "Diagnostic badge renders health state",
  () => {
    const html =
      renderRuntimeDiagnosticBadge({
        healthy: true,
        score: 100,
        grade: "A",
      });

    assert.ok(
      html.includes(
        "HEALTHY",
      ),
    );

    assert.ok(
      html.includes(
        "Grade A",
      ),
    );
  },
);