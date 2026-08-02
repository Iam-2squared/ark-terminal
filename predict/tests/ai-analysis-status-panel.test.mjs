import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAIAnalysisStatusViewModel,
  mountAIAnalysisStatus,
  renderAIAnalysisStatus,
} from "../analysis/ai-analysis-status-panel.js";

test(
  "Status view model is built",
  () => {
    const result =
      buildAIAnalysisStatusViewModel({
        status:
          "running",

        symbol:
          "7203.T",
      });

    assert.equal(
      result.status,
      "running",
    );

    assert.equal(
      result.symbol,
      "7203.T",
    );

    assert.equal(
      result.busy,
      true,
    );

    assert.equal(
      result.successful,
      false,
    );
  },
);

test(
  "Status HTML is rendered",
  () => {
    const html =
      renderAIAnalysisStatus({
        status:
          "success",

        symbol:
          "7203.T",
      });

    assert.ok(
      html.includes(
        "AI ANALYSIS STATUS",
      ),
    );

    assert.ok(
      html.includes(
        "AI分析が完了しました",
      ),
    );

    assert.ok(
      html.includes(
        "7203.T",
      ),
    );
  },
);

test(
  "Unknown status becomes idle",
  () => {
    const result =
      buildAIAnalysisStatusViewModel({
        status:
          "invalid",
      });

    assert.equal(
      result.status,
      "idle",
    );

    assert.equal(
      result.busy,
      false,
    );
  },
);

test(
  "Status panel mounts",
  () => {
    const container = {
      innerHTML:
        "",

      dataset:
        {},

      hidden:
        false,
    };

    const documentRef = {
      querySelector() {
        return container;
      },

      createElement() {
        return container;
      },

      body: {
        appendChild() {},
      },
    };

    const result =
      mountAIAnalysisStatus({
        documentRef,

        input: {
          status:
            "running",

          symbol:
            "AAA",
        },
      });

    assert.equal(
      result.mounted,
      true,
    );

    assert.equal(
      container.dataset
        .aiStatus,
      "running",
    );

    assert.equal(
      container.hidden,
      false,
    );

    assert.ok(
      container.innerHTML.includes(
        "AAA",
      ),
    );
  },
);