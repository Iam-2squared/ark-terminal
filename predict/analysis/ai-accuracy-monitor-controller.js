import {
  getPredictions,
  getPredictionsAsync,
} from "../backtest/storage.js";
import { buildAIAccuracyMonitorReport } from "./ai-accuracy-monitor-engine.js";
import { buildAIAccuracyMonitorViewModel } from "./ai-accuracy-monitor-view-model.js";
import {
  mountAIAccuracyMonitor,
  renderAIAccuracyMonitor,
} from "./ai-accuracy-monitor-ui.js";

export class AIAccuracyMonitorController {
  constructor({
    recordProvider = getPredictions,
    archiveProvider = null,
    reportBuilder = buildAIAccuracyMonitorReport,
    viewModelBuilder = buildAIAccuracyMonitorViewModel,
    mount = mountAIAccuracyMonitor,
    renderer = renderAIAccuracyMonitor,
    documentRef = globalThis.document ?? null,
    eventTarget = globalThis.window ?? null,
  } = {}) {
    this.recordProvider = recordProvider;
    this.archiveProvider = archiveProvider;
    this.reportBuilder = reportBuilder;
    this.viewModelBuilder = viewModelBuilder;
    this.mount = mount;
    this.renderer = renderer;
    this.documentRef = documentRef;
    this.eventTarget = eventTarget;
    this.root = null;
    this.started = false;
    this.lastReport = null;
    this.lastViewModel = null;
    this.handleRefresh = () => this.refresh();
  }

  renderRecords(records) {
    const report = this.reportBuilder(records);
    const viewModel = this.viewModelBuilder(report);
    const result = this.renderer(viewModel, this.root);

    this.lastReport = report;
    this.lastViewModel = viewModel;

    return {
      ...result,
      report,
      viewModel,
    };
  }

  refresh() {
    if (!this.root) {
      return {
        rendered: false,
        reason: "container_unavailable",
      };
    }

    try {
      const records = this.recordProvider();
      return this.renderRecords(records);
    } catch (error) {
      const viewModel = this.viewModelBuilder(null, { error });
      const result = this.renderer(viewModel, this.root);

      this.lastReport = null;
      this.lastViewModel = viewModel;

      return {
        ...result,
        error,
        viewModel,
      };
    }
  }

  async hydrate() {
    if (!this.root || typeof this.archiveProvider !== "function") {
      return { rendered: false, reason: "archive_unavailable" };
    }

    try {
      return this.renderRecords(await this.archiveProvider());
    } catch (error) {
      return { rendered: false, reason: "archive_read_failed", error };
    }
  }

  start() {
    if (this.started) {
      return {
        started: true,
        reused: true,
        controller: this,
      };
    }

    const mounted = this.mount({
      documentRef: this.documentRef,
    });

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
    this.eventTarget?.addEventListener?.("storage", this.handleRefresh);
    this.eventTarget?.addEventListener?.(
      "ark:prediction-outcomes-updated",
      this.handleRefresh,
    );
    this.started = true;

    return {
      started: true,
      reused: mounted.reused === true,
      controller: this,
      refresh: this.refresh(),
      hydration: this.hydrate(),
    };
  }

  stop() {
    this.eventTarget?.removeEventListener?.(
      "ark:analysis-ready",
      this.handleRefresh,
    );
    this.eventTarget?.removeEventListener?.("storage", this.handleRefresh);
    this.eventTarget?.removeEventListener?.(
      "ark:prediction-outcomes-updated",
      this.handleRefresh,
    );
    this.started = false;

    return {
      stopped: true,
    };
  }
}

let activeController = null;

export function initAIAccuracyMonitor(options = {}) {
  activeController?.stop();
  activeController = new AIAccuracyMonitorController({
    archiveProvider: getPredictionsAsync,
    ...options,
  });
  const result = activeController.start();

  return result.controller;
}

export function stopAIAccuracyMonitor() {
  activeController?.stop();
  activeController = null;
}
