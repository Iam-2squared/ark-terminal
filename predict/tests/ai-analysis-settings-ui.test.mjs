import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAISettingsViewModel,
  readSettingsForm,
  renderAIAnalysisSettings,
} from "../analysis/ai-analysis-settings-ui.js";

test(
  "Settings view model is normalized",
  () => {
    const result =
      buildAISettingsViewModel({
        capital:
          500000,

        allocation:
          0.4,

        lotSize:
          100,

        weights: {
          technical:
            2,

          ai:
            1.5,

          macro:
            1,
        },
      });

    assert.equal(
      result.capital,
      500000,
    );

    assert.equal(
      result.allocationPercent,
      40,
    );

    assert.equal(
      result.weights.technical,
      2,
    );
  },
);

test(
  "Settings HTML is rendered",
  () => {
    const html =
      renderAIAnalysisSettings({
        capital:
          300000,

        allocation:
          0.3,
      });

    assert.ok(
      html.includes(
        "AI ANALYSIS SETTINGS",
      ),
    );

    assert.ok(
      html.includes(
        "運用資金",
      ),
    );

    assert.ok(
      html.includes(
        'value="300000"',
      ),
    );

    assert.ok(
      html.includes(
        "分析ウェイト",
      ),
    );
  },
);

test(
  "Settings form is read",
  () => {
    const values = {
      capital:
        "400000",

      allocationPercent:
        "35",

      lotSize:
        "100",

      stopPercent:
        "4",

      targetPercent:
        "12",

      maximumRiskPercent:
        "5",

      minimumConfidence:
        "65",

      minimumScore:
        "70",

      weightTechnical:
        "2",

      weightAI:
        "1.5",

      weightMacro:
        "1",
    };

    const container = {
      querySelector(selector) {
        const match =
          selector.match(
            /\[name="([^"]+)"\]/,
          );

        return {
          value:
            values[
              match?.[1]
            ],
        };
      },
    };

    const result =
      readSettingsForm(
        container,
      );

    assert.equal(
      result.capital,
      400000,
    );

    assert.equal(
      result.allocation,
      0.35,
    );

    assert.equal(
      result.minimumScore,
      70,
    );

    assert.equal(
      result.weights.ai,
      1.5,
    );
  },
);