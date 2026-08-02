import { fetchHistory } from "../data.js";
import {
  getPredictionsAsync,
  setPredictions,
} from "../backtest/storage.js";
import { refreshPredictionOutcomes } from "./prediction-outcome-service.js";

export const DEFAULT_OUTCOME_REFRESH_INTERVAL_MS = 6 * 60 * 60 * 1000;
export const DEFAULT_OUTCOME_REFRESH_THROTTLE_MS = 5 * 60 * 1000;

function eventWithDetail(name, detail) {
  if (typeof globalThis.CustomEvent === "function") {
    return new globalThis.CustomEvent(name, { detail });
  }

  return { type: name, detail };
}

export class PredictionOutcomeController {
  constructor({
    recordProvider = getPredictionsAsync,
    recordWriter = setPredictions,
    historyProvider = fetchHistory,
    refresher = refreshPredictionOutcomes,
    eventTarget = globalThis.window ?? null,
    now = Date.now,
    intervalMs = DEFAULT_OUTCOME_REFRESH_INTERVAL_MS,
    throttleMs = DEFAULT_OUTCOME_REFRESH_THROTTLE_MS,
    setIntervalFn = globalThis.setInterval?.bind(globalThis),
    clearIntervalFn = globalThis.clearInterval?.bind(globalThis),
  } = {}) {
    if (typeof recordProvider !== "function") {
      throw new TypeError("Prediction outcome record provider is invalid.");
    }
    if (typeof recordWriter !== "function") {
      throw new TypeError("Prediction outcome record writer is invalid.");
    }
    if (typeof historyProvider !== "function") {
      throw new TypeError("Prediction outcome history provider is invalid.");
    }
    if (typeof refresher !== "function") {
      throw new TypeError("Prediction outcome refresher is invalid.");
    }
    if (typeof now !== "function") {
      throw new TypeError("Prediction outcome clock is invalid.");
    }

    this.recordProvider = recordProvider;
    this.recordWriter = recordWriter;
    this.historyProvider = historyProvider;
    this.refresher = refresher;
    this.eventTarget = eventTarget;
    this.now = now;
    this.intervalMs = Math.max(0, Number(intervalMs) || 0);
    this.throttleMs = Math.max(0, Number(throttleMs) || 0);
    this.setIntervalFn = setIntervalFn;
    this.clearIntervalFn = clearIntervalFn;
    this.lastStartedAt = null;
    this.activeRefresh = null;
    this.intervalHandle = null;
    this.started = false;
    this.handleWake = () => void this.refresh();
  }

  async runRefresh() {
    this.lastStartedAt = Number(this.now());
    const records = await this.recordProvider();
    const report = await this.refresher({
      records,
      fetchHistory: this.historyProvider,
    });

    if (report.changed) {
      this.recordWriter(report.records);
    }

    this.eventTarget?.dispatchEvent?.(
      eventWithDetail("ark:prediction-outcomes-updated", report),
    );

    return report;
  }

  refresh({ force = false } = {}) {
    if (this.activeRefresh) return this.activeRefresh;

    const elapsed =
      this.lastStartedAt === null
        ? Number.POSITIVE_INFINITY
        : Number(this.now()) - this.lastStartedAt;

    if (!force && elapsed < this.throttleMs) {
      return Promise.resolve({
        status: "throttled",
        changed: false,
        executionAllowed: false,
      });
    }

    this.activeRefresh = this.runRefresh().finally(() => {
      this.activeRefresh = null;
    });

    return this.activeRefresh;
  }

  start() {
    if (this.started) {
      return { started: true, reused: true, controller: this };
    }

    this.started = true;
    this.eventTarget?.addEventListener?.("focus", this.handleWake);
    this.eventTarget?.addEventListener?.("online", this.handleWake);

    if (this.intervalMs > 0 && typeof this.setIntervalFn === "function") {
      this.intervalHandle = this.setIntervalFn(
        this.handleWake,
        this.intervalMs,
      );
    }

    return {
      started: true,
      reused: false,
      controller: this,
      refresh: this.refresh({ force: true }),
    };
  }

  stop() {
    this.eventTarget?.removeEventListener?.("focus", this.handleWake);
    this.eventTarget?.removeEventListener?.("online", this.handleWake);

    if (this.intervalHandle !== null && typeof this.clearIntervalFn === "function") {
      this.clearIntervalFn(this.intervalHandle);
    }

    this.intervalHandle = null;
    this.started = false;
    return { stopped: true };
  }
}

let activeController = null;

export function initPredictionOutcomeController(options = {}) {
  activeController?.stop();
  activeController = new PredictionOutcomeController(options);
  activeController.start();
  return activeController;
}

export function stopPredictionOutcomeController() {
  activeController?.stop();
  activeController = null;
}

export const PredictionOutcomeControllerInternals = Object.freeze({
  eventWithDetail,
});

export default PredictionOutcomeController;
