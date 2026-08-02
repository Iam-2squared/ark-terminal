import { buildAIAnalysisInput } from "./ai-analysis-input-builder.js";
import { marketIntelligenceRuntimeAdapter } from "./market-intelligence-runtime-adapter.js";
import { buildMarketIntelligenceDashboardViewModel } from "./market-intelligence-dashboard-view-model.js";
import {
  mountMarketIntelligenceDashboard,
  renderMarketIntelligenceDashboard,
} from "./market-intelligence-dashboard-presenter.js";

export const MARKET_INTELLIGENCE_DASHBOARD_EVENT =
  "ark:market-intelligence-dashboard";

function eventWithDetail(name, detail) {
  if (typeof globalThis.CustomEvent === "function") {
    return new globalThis.CustomEvent(name, { detail });
  }

  return { type: name, detail };
}

function reportPhase(report) {
  const status = String(report?.status ?? "").toLowerCase();
  const featureStatus = String(
    report?.featureStatus ?? report?.result?.features?.status ?? "",
  ).toLowerCase();

  if (status === "error" || report?.error) return "error";
  if (featureStatus === "ready") return "ready";
  if (
    featureStatus === "partial" ||
    status === "partial" ||
    status === "validation_required"
  ) {
    return "partial";
  }
  if (
    report?.predictions?.some(
      (prediction) =>
        prediction?.score !== null &&
        prediction?.score !== undefined &&
        Number.isFinite(Number(prediction.score)),
    )
  ) {
    return "partial";
  }

  return "unavailable";
}

function createAbortController() {
  return typeof globalThis.AbortController === "function"
    ? new globalThis.AbortController()
    : null;
}

export class MarketIntelligenceDashboardController {
  constructor({
    stateProvider,
    inputBuilder = buildAIAnalysisInput,
    runtimeAdapter = marketIntelligenceRuntimeAdapter,
    viewModelBuilder = buildMarketIntelligenceDashboardViewModel,
    mount = mountMarketIntelligenceDashboard,
    renderer = renderMarketIntelligenceDashboard,
    documentRef = globalThis.document ?? null,
    eventTarget = globalThis.window ?? globalThis,
    abortControllerFactory = createAbortController,
  } = {}) {
    if (typeof stateProvider !== "function") {
      throw new TypeError("Market Intelligence state provider is required.");
    }
    if (typeof inputBuilder !== "function") {
      throw new TypeError("Market Intelligence input builder is invalid.");
    }
    if (!runtimeAdapter || typeof runtimeAdapter.analyze !== "function") {
      throw new TypeError("Market Intelligence runtime adapter is invalid.");
    }
    if (typeof viewModelBuilder !== "function") {
      throw new TypeError("Market Intelligence view model builder is invalid.");
    }
    if (typeof renderer !== "function" || typeof mount !== "function") {
      throw new TypeError("Market Intelligence presenter is invalid.");
    }

    this.stateProvider = stateProvider;
    this.inputBuilder = inputBuilder;
    this.runtimeAdapter = runtimeAdapter;
    this.viewModelBuilder = viewModelBuilder;
    this.mount = mount;
    this.renderer = renderer;
    this.documentRef = documentRef;
    this.eventTarget = eventTarget;
    this.abortControllerFactory = abortControllerFactory;
    this.root = null;
    this.started = false;
    this.generation = 0;
    this.abortController = null;
    this.lastReport = null;
    this.lastViewModel = null;
    this.handleRefresh = () => void this.refresh();
  }

  render({ report = null, state = {}, phase = null, error = null } = {}) {
    const viewModel = this.viewModelBuilder({ report, state, phase, error });
    const result = this.renderer(viewModel, this.root);

    this.lastReport = report;
    this.lastViewModel = viewModel;

    return { ...result, report, viewModel };
  }

  dispatchReport(report, viewModel) {
    this.eventTarget?.dispatchEvent?.(
      eventWithDetail(MARKET_INTELLIGENCE_DASHBOARD_EVENT, {
        version: viewModel.version,
        status: viewModel.status.key,
        symbol: viewModel.symbol,
        selectedHorizon: report?.selectedHorizon ?? null,
        featureConfidence: report?.featureConfidence ?? null,
        featureCoverage: report?.featureCoverage ?? null,
        executionAllowed: false,
      }),
    );
  }

  async refresh() {
    if (!this.root) {
      return { rendered: false, reason: "container_unavailable" };
    }

    const generation = ++this.generation;
    this.abortController?.abort?.();
    const abortController = this.abortControllerFactory?.() ?? null;
    this.abortController = abortController;

    let state = {};

    try {
      state = this.stateProvider() ?? {};

      if (!state.symbol && !state.ticker && !state.quote?.symbol) {
        return this.render({ state, phase: "idle" });
      }

      this.render({ state, phase: "loading" });

      const input = this.inputBuilder({
        state,
        settings: {
          marketIntelligence: { captureHistoricalSnapshots: false },
        },
      });

      if (!input?.marketIntelligence) {
        const result = this.render({ state, phase: "unavailable" });
        this.dispatchReport(null, result.viewModel);
        return result;
      }

      const report = await this.runtimeAdapter.analyze({
        ...input,
        signal: abortController?.signal,
      });

      if (generation !== this.generation || abortController?.signal?.aborted) {
        return { rendered: false, reason: "stale_request" };
      }

      const result = this.render({
        report,
        state,
        phase: reportPhase(report),
        error: report?.status === "error" ? report.error : null,
      });
      this.dispatchReport(report, result.viewModel);
      return result;
    } catch (error) {
      if (
        generation !== this.generation ||
        abortController?.signal?.aborted ||
        error?.name === "AbortError"
      ) {
        return { rendered: false, reason: "stale_request" };
      }

      const result = this.render({ state, phase: "error", error });
      this.dispatchReport(null, result.viewModel);
      return { ...result, error };
    } finally {
      if (this.abortController === abortController) {
        this.abortController = null;
      }
    }
  }

  start() {
    if (this.started) {
      return { started: true, reused: true, controller: this };
    }

    const mounted = this.mount({ documentRef: this.documentRef });
    if (!mounted?.mounted || !mounted.root) {
      return {
        started: false,
        reason: mounted?.reason ?? "mount_failed",
        controller: this,
      };
    }

    this.root = mounted.root;
    this.eventTarget?.addEventListener?.(
      "ark:analysis-ready",
      this.handleRefresh,
    );
    this.started = true;

    const refresh = this.refresh();

    return {
      started: true,
      reused: mounted.reused === true,
      controller: this,
      refresh,
    };
  }

  stop() {
    this.eventTarget?.removeEventListener?.(
      "ark:analysis-ready",
      this.handleRefresh,
    );
    this.generation += 1;
    this.abortController?.abort?.();
    this.abortController = null;
    this.started = false;

    return { stopped: true };
  }
}

let activeController = null;

export function initMarketIntelligenceDashboardController(options = {}) {
  activeController?.stop();
  activeController = new MarketIntelligenceDashboardController(options);
  const result = activeController.start();
  return result.controller;
}

export function stopMarketIntelligenceDashboardController() {
  activeController?.stop();
  activeController = null;
}

export const MarketIntelligenceDashboardControllerInternals = Object.freeze({
  eventWithDetail,
  reportPhase,
  createAbortController,
});

export default MarketIntelligenceDashboardController;
