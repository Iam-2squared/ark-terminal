import { getPredictionsAsync } from "../backtest/storage.js";
import { loadWeights } from "../analysis/weights.js";
import { buildResolvedFeedback } from "./resolved-feedback-service.js";
import { LearningFeedbackRepository } from "./learning-feedback-repository.js";

function eventWithDetail(name, detail) {
  if (typeof globalThis.CustomEvent === "function") {
    return new globalThis.CustomEvent(name, { detail });
  }
  return { type: name, detail };
}

export class ResolvedFeedbackController {
  constructor({
    recordProvider = getPredictionsAsync,
    weightProvider = loadWeights,
    feedbackBuilder = buildResolvedFeedback,
    repository = new LearningFeedbackRepository(),
    eventTarget = globalThis.window ?? null,
  } = {}) {
    if (typeof recordProvider !== "function") {
      throw new TypeError("Resolved feedback record provider is invalid.");
    }
    if (typeof weightProvider !== "function") {
      throw new TypeError("Resolved feedback weight provider is invalid.");
    }
    if (typeof feedbackBuilder !== "function") {
      throw new TypeError("Resolved feedback builder is invalid.");
    }
    if (!repository || typeof repository.append !== "function") {
      throw new TypeError("Resolved feedback repository is invalid.");
    }

    this.recordProvider = recordProvider;
    this.weightProvider = weightProvider;
    this.feedbackBuilder = feedbackBuilder;
    this.repository = repository;
    this.eventTarget = eventTarget;
    this.activeRefresh = null;
    this.started = false;
    this.handleRefresh = () => void this.refresh();
  }

  refresh() {
    if (this.activeRefresh) return this.activeRefresh;

    this.activeRefresh = Promise.resolve()
      .then(async () => {
        const report = this.feedbackBuilder({
          records: await this.recordProvider(),
          currentWeights: this.weightProvider(),
        });
        const stored =
          report.audit.resolvedCount > 0
            ? this.repository.append(report)
            : { report: null, inserted: false };

        this.eventTarget?.dispatchEvent?.(
          eventWithDetail("ark:learning-feedback-ready", {
            report,
            persisted: stored.inserted,
          }),
        );

        return { report, persisted: stored.inserted };
      })
      .finally(() => {
        this.activeRefresh = null;
      });

    return this.activeRefresh;
  }

  start() {
    if (this.started) {
      return { started: true, reused: true, controller: this };
    }
    this.started = true;
    this.eventTarget?.addEventListener?.(
      "ark:prediction-outcomes-updated",
      this.handleRefresh,
    );
    return {
      started: true,
      reused: false,
      controller: this,
      refresh: this.refresh(),
    };
  }

  stop() {
    this.eventTarget?.removeEventListener?.(
      "ark:prediction-outcomes-updated",
      this.handleRefresh,
    );
    this.started = false;
    return { stopped: true };
  }
}

let activeController = null;

export function initResolvedFeedbackController(options = {}) {
  activeController?.stop();
  activeController = new ResolvedFeedbackController(options);
  activeController.start();
  return activeController;
}

export function stopResolvedFeedbackController() {
  activeController?.stop();
  activeController = null;
}

export const ResolvedFeedbackControllerInternals = Object.freeze({
  eventWithDetail,
});

export default ResolvedFeedbackController;
