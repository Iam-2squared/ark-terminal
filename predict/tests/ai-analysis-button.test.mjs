import assert from "node:assert/strict";
import test from "node:test";

import {
  createAIAnalysisButton,
  installAIAnalysisButton,
  setAIAnalysisButtonState,
} from "../analysis/ai-analysis-button.js";

function createElement(
  tagName,
) {
  return {
    tagName,

    id: "",

    type: "",

    className: "",

    textContent: "",

    disabled: false,

    dataset: {},

    children: [],

    appendChild(child) {
      this.children.push(
        child,
      );
    },

    insertAdjacentElement(
      position,
      element,
    ) {
      this.inserted = {
        position,
        element,
      };
    },
  };
}

test(
  "AI analysis button is created",
  () => {
    const documentRef = {
      querySelector() {
        return null;
      },

      createElement,
    };

    const button =
      createAIAnalysisButton({
        documentRef,
      });

    assert.equal(
      button.id,
      "aiAnalysisButton",
    );

    assert.equal(
      button.type,
      "button",
    );

    assert.equal(
      button.textContent,
      "AI分析を実行",
    );

    assert.equal(
      button.dataset
        .aiAnalysisState,
      "ready",
    );
  },
);

test(
  "AI analysis button is installed",
  () => {
    const anchor =
      createElement(
        "section",
      );

    const documentRef = {
      querySelector(selector) {
        if (
          selector ===
          "#aiAnalysisButton"
        ) {
          return null;
        }

        if (
          selector ===
          "#aiAnalysis"
        ) {
          return anchor;
        }

        return null;
      },

      createElement,

      body:
        createElement(
          "body",
        ),
    };

    const result =
      installAIAnalysisButton({
        documentRef,
      });

    assert.equal(
      result.installed,
      true,
    );

    assert.equal(
      result.reused,
      false,
    );

    assert.equal(
      result.button.id,
      "aiAnalysisButton",
    );

    assert.equal(
      anchor.inserted
        .position,
      "afterend",
    );
  },
);

test(
  "Existing button is reused",
  () => {
    const existing =
      createElement(
        "button",
      );

    existing.id =
      "aiAnalysisButton";

    const documentRef = {
      querySelector(selector) {
        return selector ===
          "#aiAnalysisButton"
          ? existing
          : null;
      },
    };

    const result =
      installAIAnalysisButton({
        documentRef,
      });

    assert.equal(
      result.installed,
      true,
    );

    assert.equal(
      result.reused,
      true,
    );

    assert.equal(
      result.button,
      existing,
    );
  },
);

test(
  "Button state is updated",
  () => {
    const button =
      createElement(
        "button",
      );

    setAIAnalysisButtonState({
      button,
      state:
        "running",
    });

    assert.equal(
      button.disabled,
      true,
    );

    assert.equal(
      button.textContent,
      "AI分析中...",
    );

    assert.equal(
      button.dataset
        .aiAnalysisState,
      "running",
    );

    setAIAnalysisButtonState({
      button,
      state:
        "error",
    });

    assert.equal(
      button.disabled,
      false,
    );

    assert.equal(
      button.textContent,
      "再試行",
    );
  },
);