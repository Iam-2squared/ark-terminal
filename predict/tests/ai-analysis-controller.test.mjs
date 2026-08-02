import assert from "node:assert/strict";
import test from "node:test";

import {
  AIAnalysisController,
  connectAIAnalysisButton,
} from "../analysis/ai-analysis-controller.js";

function createEventTarget() {
  const events = [];

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

    events,

    dispatchEvent(event) {
      events.push(event);
      return true;
    },
  };
}

test(
  "Controller executes analysis",
  async () => {
    const eventTarget =
      createEventTarget();

    const controller =
      new AIAnalysisController({
        eventTarget,

        runner:
          async (input) => ({
            symbol:
              input.symbol,

            action:
              "BUY",
          }),
      });

    const response =
      await controller.analyze({
        symbol:
          "7203.T",
      });

    assert.equal(
      response.status,
      "ready",
    );

    assert.equal(
      response.result.symbol,
      "7203.T",
    );

    assert.equal(
      controller.lastResult
        .action,
      "BUY",
    );

    assert.ok(
      eventTarget.events.some(
        (event) =>
          event.type ===
          "ark:ai-analysis-complete",
      ),
    );
  },
);

test(
  "Controller handles errors",
  async () => {
    const eventTarget =
      createEventTarget();

    const controller =
      new AIAnalysisController({
        eventTarget,

        runner:
          async () => {
            throw new Error(
              "analysis failed",
            );
          },
      });

    const response =
      await controller.analyze({});

    assert.equal(
      response.status,
      "error",
    );

    assert.equal(
      response.error.message,
      "analysis failed",
    );

    assert.ok(
      eventTarget.events.some(
        (event) =>
          event.type ===
          "ark:ai-analysis-error",
      ),
    );
  },
);

test(
  "Busy controller rejects duplicate execution",
  async () => {
    let release;

    const pending =
      new Promise(
        (resolve) => {
          release =
            resolve;
        },
      );

    const controller =
      new AIAnalysisController({
        eventTarget:
          createEventTarget(),

        runner:
          async () => {
            await pending;

            return {
              action:
                "HOLD",
            };
          },
      });

    const first =
      controller.analyze({});

    const second =
      await controller.analyze({});

    assert.equal(
      second.status,
      "busy",
    );

    release();

    await first;
  },
);

test(
  "Button connection runs controller",
  async () => {
    let clickHandler =
      null;

    const button = {
      disabled:
        false,

      dataset:
        {},

      addEventListener(
        name,
        handler,
      ) {
        if (name === "click") {
          clickHandler =
            handler;
        }
      },

      removeEventListener() {},
    };

    const documentRef = {
      querySelector() {
        return button;
      },
    };

    let calls = 0;

    const cleanup =
      connectAIAnalysisButton({
        controller: {
          async analyze(input) {
            calls++;

            assert.equal(
              input.symbol,
              "AAA",
            );
          },
        },

        documentRef,

        inputProvider:
          () => ({
            symbol:
              "AAA",
          }),
      });

    await clickHandler();

    assert.equal(
      calls,
      1,
    );

    assert.equal(
      button.disabled,
      false,
    );

    assert.equal(
      button.dataset
        .aiAnalysisState,
      "ready",
    );

    cleanup();
  },
);