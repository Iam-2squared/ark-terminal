import assert from "node:assert/strict";
import test from "node:test";

import {
  createAIAnalysisApplication,
  startAIAnalysisApplication,
  stopAIAnalysisApplication,
} from "../analysis/ai-analysis-entry.js";

function createWindowRef() {
  const listeners =
    new Map();

  class FakeCustomEvent {
    constructor(
      type,
      options = {},
    ) {
      this.type =
        type;

      this.detail =
        options.detail;
    }
  }

  return {
    CustomEvent:
      FakeCustomEvent,

    __ARK_ANALYSIS_INPUT__: {
      symbol:
        "7203.T",
    },

    addEventListener(
      name,
      handler,
    ) {
      const current =
        listeners.get(name) ??
        [];

      current.push(handler);

      listeners.set(
        name,
        current,
      );
    },

    removeEventListener(
      name,
      handler,
    ) {
      const current =
        listeners.get(name) ??
        [];

      listeners.set(
        name,
        current.filter(
          (item) =>
            item !== handler,
        ),
      );
    },

    dispatchEvent(event) {
      const handlers =
        listeners.get(
          event.type,
        ) ?? [];

      for (const handler of handlers) {
        handler(event);
      }

      return true;
    },

    listenerCount(name) {
      return (
        listeners.get(name) ??
        []
      ).length;
    },
  };
}

function createDocumentRef() {
  const button = {
    disabled:
      false,

    dataset:
      {},

    addEventListener() {},

    removeEventListener() {},
  };

  const container = {
    innerHTML:
      "",

    dataset:
      {},
  };

  return {
    button,
    container,

    querySelector(selector) {
      if (
        selector.includes(
          "aiAnalysisButton",
        )
      ) {
        return button;
      }

      return container;
    },

    createElement() {
      return {
        innerHTML:
          "",

        dataset:
          {},

        className:
          "",

        id:
          "",
      };
    },

    body: {
      appendChild() {},
    },
  };
}

test(
  "Application requires browser environment",
  () => {
    const result =
      createAIAnalysisApplication({
        windowRef:
          null,

        documentRef:
          null,
      });

    assert.equal(
      result.started,
      false,
    );

    assert.equal(
      result.controller,
      null,
    );
  },
);

test(
  "Application starts analysis controller",
  async () => {
    const windowRef =
      createWindowRef();

    const documentRef =
      createDocumentRef();

    const application =
      createAIAnalysisApplication({
        windowRef,
        documentRef,

        runner:
          async (input) => ({
            symbol:
              input.symbol,

            action:
              "BUY",

            score:
              80,
          }),
      });

    const response =
      await application.analyze();

    assert.equal(
      application.started,
      true,
    );

    assert.equal(
      response.status,
      "ready",
    );

    assert.equal(
      response.result.symbol,
      "7203.T",
    );

    assert.equal(
      response.result.action,
      "BUY",
    );

    assert.ok(
      windowRef.ArkAIAnalysis,
    );

    application.stop();
  },
);

test(
  "Presenter listener receives completed result",
  async () => {
    const windowRef =
      createWindowRef();

    const documentRef =
      createDocumentRef();

    const application =
      createAIAnalysisApplication({
        windowRef,
        documentRef,

        runner:
          async () => ({
            symbol:
              "AAA",

            action:
              "BUY",

            score:
              80,

            confidence:
              85,

            agreementRate:
              75,
          }),
      });

    await application.analyze();

    assert.ok(
      documentRef
        .container
        .innerHTML
        .includes(
          "AI ANALYSIS RESULT",
        ),
    );

    assert.equal(
      documentRef
        .container
        .dataset
        .aiResultState,
      "ready",
    );

    application.stop();
  },
);

test(
  "Global start and stop API works",
  () => {
    const windowRef =
      createWindowRef();

    const documentRef =
      createDocumentRef();

    const application =
      startAIAnalysisApplication({
        windowRef,
        documentRef,

        runner:
          async () => ({
            action:
              "HOLD",
          }),
      });

    assert.equal(
      application.started,
      true,
    );

    stopAIAnalysisApplication();
  },
);