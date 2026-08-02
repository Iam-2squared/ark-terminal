import assert from "node:assert/strict";
import test from "node:test";

import { ResolvedFeedbackController } from "../learning/resolved-feedback-controller.js";

test("Resolved feedback controller stores candidates but never applies weights", async () => {
  const appended = [];
  const events = [];
  const controller = new ResolvedFeedbackController({
    recordProvider: async () => [{ id: "resolved" }],
    weightProvider: () => ({ rsi: 1 }),
    feedbackBuilder: ({ records, currentWeights }) => ({
      id: "feedback",
      records,
      currentWeights,
      audit: { resolvedCount: 1, activeWeightsChanged: false },
      executionAllowed: false,
    }),
    repository: {
      append(report) {
        appended.push(report);
        return { report, inserted: true };
      },
    },
    eventTarget: {
      addEventListener() {},
      removeEventListener() {},
      dispatchEvent(event) {
        events.push(event);
      },
    },
  });

  const result = await controller.refresh();
  assert.equal(result.persisted, true);
  assert.equal(appended.length, 1);
  assert.equal(appended[0].audit.activeWeightsChanged, false);
  assert.equal(events[0].type, "ark:learning-feedback-ready");
});
