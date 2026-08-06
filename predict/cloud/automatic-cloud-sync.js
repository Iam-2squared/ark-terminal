import {
  getPredictionsAsync,
  setPredictions,
} from "../backtest/storage.js";

import {
  CloudSyncError,
  getCloudSyncStatus,
  saveCloudRecord,
} from "./cloud-sync-client.js";

import {
  loadPredictionStateFromCloud,
  mergePredictionRecords,
  savePredictionToCloud,
  syncPredictionRecordsToCloud,
} from "./prediction-cloud-repository.js";

export const AUTOMATIC_CLOUD_SYNC_VERSION =
  "automatic-cloud-sync-v1";

const LEARNING_REPORT_COLLECTION = "learning_reports";

function eventWithDetail(name, detail) {
  if (typeof globalThis.CustomEvent === "function") {
    return new globalThis.CustomEvent(name, { detail });
  }

  return { type: name, detail };
}

function cloudReady(status) {
  return Boolean(
    status?.configured === true &&
    status?.storageConfigured === true &&
    status?.authenticated === true,
  );
}

function normalizedRecordId(value) {
  const id = String(value ?? "")
    .trim()
    .replace(/[^A-Za-z0-9._:-]/g, "-")
    .replace(/-+/g, "-")
    .slice(0, 160);

  return /^[A-Za-z0-9]/.test(id)
    ? id
    : `report-${id}`.slice(0, 160);
}

function recordSignature(records = []) {
  return (Array.isArray(records) ? records : [])
    .map((record) => [
      record?.id ?? null,
      record?.status ?? null,
      record?.updatedAt ?? null,
      record?.resolvedAt ?? null,
      record?.actualPrice ?? null,
      record?.hit ?? null,
    ])
    .sort((left, right) =>
      String(left[0] ?? "").localeCompare(String(right[0] ?? "")),
    );
}

function samePredictionState(first, second) {
  return JSON.stringify(recordSignature(first)) ===
    JSON.stringify(recordSignature(second));
}

function eligibleResolvedRecords(report = {}) {
  const ids = new Set(
    Array.isArray(report?.resolvedIds)
      ? report.resolvedIds.filter(Boolean)
      : [],
  );

  return (Array.isArray(report?.records) ? report.records : [])
    .filter((record) => ids.has(record?.id));
}

export class AutomaticCloudSyncController {
  constructor({
    statusProvider = getCloudSyncStatus,
    localProvider = getPredictionsAsync,
    localWriter = setPredictions,
    cloudLoader = loadPredictionStateFromCloud,
    cloudBulkWriter = syncPredictionRecordsToCloud,
    predictionWriter = savePredictionToCloud,
    cloudRecordWriter = saveCloudRecord,
    eventTarget = globalThis.window ?? null,
  } = {}) {
    for (const [name, value] of Object.entries({
      statusProvider,
      localProvider,
      localWriter,
      cloudLoader,
      cloudBulkWriter,
      predictionWriter,
      cloudRecordWriter,
    })) {
      if (typeof value !== "function") {
        throw new TypeError(`${name} must be a function.`);
      }
    }

    this.statusProvider = statusProvider;
    this.localProvider = localProvider;
    this.localWriter = localWriter;
    this.cloudLoader = cloudLoader;
    this.cloudBulkWriter = cloudBulkWriter;
    this.predictionWriter = predictionWriter;
    this.cloudRecordWriter = cloudRecordWriter;
    this.eventTarget = eventTarget;

    this.state = {
      version: AUTOMATIC_CLOUD_SYNC_VERSION,
      configured: false,
      storageConfigured: false,
      authenticated: false,
      started: false,
      lastRestoreAt: null,
      lastError: null,
    };

    this.activeRestore = null;
    this.handleOutcome = (event) => {
      void this.mirrorOutcomeReport(event?.detail);
    };
    this.handleLearning = (event) => {
      void this.mirrorLearningReport(event?.detail?.report);
    };
    this.handleOnline = () => {
      void this.refreshStatus()
        .then(() => this.restore());
    };
  }

  emit(name, detail) {
    this.eventTarget?.dispatchEvent?.(
      eventWithDetail(name, {
        version: AUTOMATIC_CLOUD_SYNC_VERSION,
        ...detail,
      }),
    );
  }

  async refreshStatus() {
    try {
      const status = await this.statusProvider();
      this.state.configured = status?.configured === true;
      this.state.storageConfigured = status?.storageConfigured === true;
      this.state.authenticated = status?.authenticated === true;
      this.state.lastError = null;
      return status;
    }
    catch (error) {
      this.state.authenticated = false;
      this.state.lastError = error?.code ?? "cloud_status_failed";
      return null;
    }
  }

  ready() {
    return cloudReady(this.state);
  }

  async restore() {
    if (this.activeRestore) return this.activeRestore;

    this.activeRestore = Promise.resolve()
      .then(async () => {
        if (!this.ready()) {
          return {
            restored: false,
            reason: "cloud_not_ready",
          };
        }

        const localRecords = await this.localProvider();
        const cloudState = await this.cloudLoader();
        const merged = mergePredictionRecords(
          localRecords,
          cloudState?.predictions ?? [],
        );
        const changed = !samePredictionState(localRecords, merged);

        if (changed) {
          this.localWriter(merged);
        }

        const mirrored = await this.cloudBulkWriter(merged);
        this.state.lastRestoreAt = new Date().toISOString();
        this.state.lastError = null;

        const result = {
          restored: true,
          changed,
          localCount: localRecords.length,
          cloudCount: cloudState?.predictions?.length ?? 0,
          mergedCount: merged.length,
          ...mirrored,
        };

        this.emit("ark:cloud-history-restored", result);
        return result;
      })
      .catch((error) => {
        if (error instanceof CloudSyncError && error.status === 401) {
          this.state.authenticated = false;
        }

        this.state.lastError =
          error?.code ??
          "cloud_restore_failed";

        const result = {
          restored: false,
          reason: this.state.lastError,
        };

        this.emit("ark:cloud-sync-error", result);
        return result;
      })
      .finally(() => {
        this.activeRestore = null;
      });

    return this.activeRestore;
  }

  async mirrorPrediction(record) {
    if (!this.ready()) {
      return {
        saved: false,
        reason: "cloud_not_ready",
      };
    }

    try {
      const result = await this.predictionWriter(record);
      this.state.lastError = null;
      this.emit("ark:cloud-prediction-saved", result);
      return result;
    }
    catch (error) {
      if (error instanceof CloudSyncError && error.status === 401) {
        this.state.authenticated = false;
      }

      this.state.lastError =
        error?.code ??
        "cloud_prediction_save_failed";

      return {
        saved: false,
        reason: this.state.lastError,
      };
    }
  }

  async mirrorOutcomeReport(report = {}) {
    if (!this.ready() || report?.changed !== true) {
      return {
        savedPredictions: 0,
        savedOutcomes: 0,
        reason: this.ready()
          ? "no_resolved_changes"
          : "cloud_not_ready",
      };
    }

    const records = eligibleResolvedRecords(report);

    if (records.length === 0) {
      return {
        savedPredictions: 0,
        savedOutcomes: 0,
        reason: "no_resolved_records",
      };
    }

    try {
      const result = await this.cloudBulkWriter(records);
      this.state.lastError = null;
      this.emit("ark:cloud-outcomes-saved", {
        resolvedIds: report.resolvedIds,
        ...result,
      });
      return result;
    }
    catch (error) {
      if (error instanceof CloudSyncError && error.status === 401) {
        this.state.authenticated = false;
      }

      this.state.lastError =
        error?.code ??
        "cloud_outcome_save_failed";

      return {
        savedPredictions: 0,
        savedOutcomes: 0,
        reason: this.state.lastError,
      };
    }
  }

  async mirrorLearningReport(report) {
    if (!this.ready()) {
      return {
        saved: false,
        reason: "cloud_not_ready",
      };
    }

    if (!report?.id || report?.executionAllowed !== false) {
      return {
        saved: false,
        reason: "invalid_learning_report",
      };
    }

    try {
      await this.cloudRecordWriter({
        collection: LEARNING_REPORT_COLLECTION,
        id: normalizedRecordId(report.id),
        data: report,
      });

      this.state.lastError = null;
      const result = {
        saved: true,
        id: normalizedRecordId(report.id),
      };
      this.emit("ark:cloud-learning-report-saved", result);
      return result;
    }
    catch (error) {
      if (error instanceof CloudSyncError && error.status === 401) {
        this.state.authenticated = false;
      }

      this.state.lastError =
        error?.code ??
        "cloud_learning_save_failed";

      return {
        saved: false,
        reason: this.state.lastError,
      };
    }
  }

  start() {
    if (this.state.started) {
      return {
        started: true,
        reused: true,
        controller: this,
        ready: Promise.resolve({
          restored: false,
          reason: "already_started",
        }),
      };
    }

    this.state.started = true;
    this.eventTarget?.addEventListener?.(
      "ark:prediction-outcomes-updated",
      this.handleOutcome,
    );
    this.eventTarget?.addEventListener?.(
      "ark:learning-feedback-ready",
      this.handleLearning,
    );
    this.eventTarget?.addEventListener?.(
      "online",
      this.handleOnline,
    );

    const ready = this.refreshStatus()
      .then(() => this.restore());

    return {
      started: true,
      reused: false,
      controller: this,
      ready,
    };
  }

  stop() {
    this.eventTarget?.removeEventListener?.(
      "ark:prediction-outcomes-updated",
      this.handleOutcome,
    );
    this.eventTarget?.removeEventListener?.(
      "ark:learning-feedback-ready",
      this.handleLearning,
    );
    this.eventTarget?.removeEventListener?.(
      "online",
      this.handleOnline,
    );
    this.state.started = false;
    return { stopped: true };
  }
}

let activeController = null;

export function initAutomaticCloudSync(options = {}) {
  activeController?.stop();
  activeController = new AutomaticCloudSyncController(options);
  const started = activeController.start();

  return {
    controller: activeController,
    ready: started.ready,
  };
}

export function stopAutomaticCloudSync() {
  activeController?.stop();
  activeController = null;
}

export const AutomaticCloudSyncInternals = Object.freeze({
  LEARNING_REPORT_COLLECTION,
  cloudReady,
  eligibleResolvedRecords,
  eventWithDetail,
  normalizedRecordId,
  recordSignature,
  samePredictionState,
});

export default AutomaticCloudSyncController;
