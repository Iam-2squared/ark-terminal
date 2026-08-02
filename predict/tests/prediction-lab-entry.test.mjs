import assert from "node:assert/strict";
import test from "node:test";

import {
  createPredictionLabRuntime,
} from "../analysis/prediction-lab-entry.js";

function createEventTarget() {
  const listeners =
    new Map();

  return {
    __ARK_ANALYSIS_STATE__:
      null,

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

    listenerCount(name) {
      return (
        listeners.get(name) ??
        []
      ).length;
    },
  };
}

test(
  "Runtime requires browser environment",
  () => {
    const runtime =
      createPredictionLabRuntime({
        windowRef: null,
        documentRef: null,
      });

    assert.equal(
      runtime.started,
      false,
    );
  },
);

test(
  "Runtime registers one listener per event",
  () => {
    const windowRef =
      createEventTarget();

    const documentRef = {
      querySelector() {
        return {
          innerHTML: "",
          dataset: {},
        };
      },

      createElement() {
        return {
          id: "",
          className: "",
          innerHTML: "",
          dataset: {},
        };
      },

      body: {
        appendChild() {},
      },
    };

    const runtime =
      createPredictionLabRuntime({
        windowRef,
        documentRef,
      });

    assert.equal(
      runtime.started,
      true,
    );

    assert.equal(
      windowRef.listenerCount(
        "ark:analysis-ready",
      ),
      1,
    );

    runtime.stop();

    assert.equal(
      windowRef.listenerCount(
        "ark:analysis-ready",
      ),
      0,
    );
  },
);