import { buildAIAnalysisInput } from "./ai-analysis-input-builder.js";
import { executeRuntimeV3Sync } from "./runtime-v3.js";
import {
  historicalMarketSnapshotService,
} from "../market-intelligence/historical-market-snapshot-service.js";

export const DAILY_MARKET_SNAPSHOT_VERSION =
  "daily-market-snapshot-controller-v1";
export const DEFAULT_DAILY_SNAPSHOT_INTERVAL_MS = 6 * 60 * 60 * 1000;

function timestampMilliseconds(value) {
  const number = Number(value);
  const timestamp = Number.isFinite(number)
    ? number < 1_000_000_000_000
      ? number * 1000
      : number
    : Date.parse(value);

  return Number.isFinite(timestamp) ? timestamp : null;
}

export function tokyoMarketDateKey(value) {
  const timestamp = timestampMilliseconds(value);
  if (timestamp === null) return null;

  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(timestamp));
}

function stateTimestamp(state, now) {
  const candle = Array.isArray(state?.history?.candles)
    ? state.history.candles.at(-1)
    : null;

  return (
    timestampMilliseconds(candle?.time) ??
    timestampMilliseconds(state?.analysisTime) ??
    Number(now())
  );
}

function normalizedSymbol(state) {
  const symbol = String(
    state?.symbol ?? state?.ticker ?? state?.quote?.symbol ?? "",
  )
    .trim()
    .toUpperCase();

  return symbol || null;
}

function eventWithDetail(name, detail) {
  if (typeof globalThis.CustomEvent === "function") {
    return new globalThis.CustomEvent(name, { detail });
  }
  return { type: name, detail };
}

export class DailyMarketSnapshotController {
  constructor({
    stateProvider,
    inputBuilder = buildAIAnalysisInput,
    runtimeRunner = executeRuntimeV3Sync,
    snapshotService = historicalMarketSnapshotService,
    eventTarget = globalThis.window ?? null,
    now = Date.now,
    intervalMs = DEFAULT_DAILY_SNAPSHOT_INTERVAL_MS,
    setIntervalFn = globalThis.setInterval?.bind(globalThis),
    clearIntervalFn = globalThis.clearInterval?.bind(globalThis),
  } = {}) {
    if (typeof stateProvider !== "function") {
      throw new TypeError("Daily snapshot state provider is required.");
    }
    if (typeof inputBuilder !== "function") {
      throw new TypeError("Daily snapshot input builder is invalid.");
    }
    if (typeof runtimeRunner !== "function") {
      throw new TypeError("Daily snapshot runtime runner is invalid.");
    }
    if (!snapshotService || typeof snapshotService.latest !== "function") {
      throw new TypeError("Daily snapshot service is invalid.");
    }
    if (typeof now !== "function") {
      throw new TypeError("Daily snapshot clock is invalid.");
    }

    this.stateProvider = stateProvider;
    this.inputBuilder = inputBuilder;
    this.runtimeRunner = runtimeRunner;
    this.snapshotService = snapshotService;
    this.eventTarget = eventTarget;
    this.now = now;
    this.intervalMs = Math.max(0, Number(intervalMs) || 0);
    this.setIntervalFn = setIntervalFn;
    this.clearIntervalFn = clearIntervalFn;
    this.activeCapture = null;
    this.intervalHandle = null;
    this.started = false;
    this.handleCapture = () => void this.capture();
  }

  runCapture() {
    const state = this.stateProvider();
    const symbol = normalizedSymbol(state);

    if (!state || !symbol) {
      return {
        version: DAILY_MARKET_SNAPSHOT_VERSION,
        status: "unavailable",
        reason: "analysis_state_unavailable",
        executionAllowed: false,
      };
    }

    const timestamp = stateTimestamp(state, this.now);
    const marketDate = tokyoMarketDateKey(timestamp);
    const latest = this.snapshotService.latest(symbol);

    if (latest && tokyoMarketDateKey(latest.asOf) === marketDate) {
      return {
        version: DAILY_MARKET_SNAPSHOT_VERSION,
        status: "duplicate",
        reason: "market_date_already_captured",
        marketDate,
        reference: {
          id: latest.id,
          symbol: latest.symbol,
          asOf: latest.asOf,
          contentFingerprint: latest.contentFingerprint,
          executionAllowed: false,
        },
        executionAllowed: false,
      };
    }

    const input = this.inputBuilder({
      state,
      settings: {
        marketIntelligence: { captureHistoricalSnapshots: true },
      },
    });
    const runtime = this.runtimeRunner({
      ...input,
      captureMarketIntelligenceSnapshot: true,
    });
    const captured = runtime?.marketIntelligenceSnapshot ?? null;

    return {
      version: DAILY_MARKET_SNAPSHOT_VERSION,
      status: captured?.status ?? "unavailable",
      reason: captured?.reason ?? null,
      marketDate,
      reference: captured?.reference ?? null,
      error: captured?.error ?? null,
      executionAllowed: false,
    };
  }

  capture() {
    if (this.activeCapture) return this.activeCapture;

    this.activeCapture = Promise.resolve()
      .then(() => this.runCapture())
      .then((report) => {
        this.eventTarget?.dispatchEvent?.(
          eventWithDetail("ark:daily-market-snapshot", report),
        );
        return report;
      })
      .catch((error) => ({
        version: DAILY_MARKET_SNAPSHOT_VERSION,
        status: "error",
        reason: "capture_failed",
        error: {
          name: error?.name ?? "Error",
          message: error?.message ?? String(error),
        },
        executionAllowed: false,
      }))
      .finally(() => {
        this.activeCapture = null;
      });

    return this.activeCapture;
  }

  start() {
    if (this.started) {
      return { started: true, reused: true, controller: this };
    }

    this.started = true;
    this.eventTarget?.addEventListener?.(
      "ark:analysis-ready",
      this.handleCapture,
    );
    this.eventTarget?.addEventListener?.("online", this.handleCapture);

    if (this.intervalMs > 0 && typeof this.setIntervalFn === "function") {
      this.intervalHandle = this.setIntervalFn(
        this.handleCapture,
        this.intervalMs,
      );
    }

    return { started: true, reused: false, controller: this };
  }

  stop() {
    this.eventTarget?.removeEventListener?.(
      "ark:analysis-ready",
      this.handleCapture,
    );
    this.eventTarget?.removeEventListener?.("online", this.handleCapture);

    if (this.intervalHandle !== null && typeof this.clearIntervalFn === "function") {
      this.clearIntervalFn(this.intervalHandle);
    }

    this.intervalHandle = null;
    this.started = false;
    return { stopped: true };
  }
}

let activeController = null;

export function initDailyMarketSnapshotController(options = {}) {
  activeController?.stop();
  activeController = new DailyMarketSnapshotController(options);
  activeController.start();
  return activeController;
}

export function stopDailyMarketSnapshotController() {
  activeController?.stop();
  activeController = null;
}

export const DailyMarketSnapshotControllerInternals = Object.freeze({
  timestampMilliseconds,
  stateTimestamp,
  normalizedSymbol,
  eventWithDetail,
});

export default DailyMarketSnapshotController;
