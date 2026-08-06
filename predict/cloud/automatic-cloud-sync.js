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

import {
  flushSharedOfflineQueue,
  getSharedOfflineQueue,
} from "./queued-cloud-writer.js";

export const AUTOMATIC_CLOUD_SYNC_VERSION =
  "automatic-cloud-sync-v2";

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
    queue = getSharedOfflineQueue(),
    queueFlusher = flushSharedOfflineQueue,
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
      queueFlusher,
    })) {
      if (typeof value !== "function") {
        throw new TypeError(`${name} must be a function.`);
      }
    }

    if (typeof queue?.enqueue !== "function") {
      throw new TypeError("queue.enqueue must be a function.");
    }

    this.statusProvider = statusProvider;
    this.localProvider = localProvider;
    this.localWriter = localWriter;
    this.cloudLoader = cloudLoader;
    this.cloudBulkWriter = cloudBulkWriter;
    this.predictionWriter = predictionWriter;
    this.cloudRecordWriter = cloudRecordWriter;
    this.queue = queue;
    this.queueFlusher = queueFlusher;
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
        .then(async () => {
          if (this.ready()) await this.queueFlusher();
          return this.restore();
        });
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

  queueRecord(record, reason) {
    const queued = this.queue.enqueue(record);
    const result = {
      saved: false,
      queued: true,
      reason,
      queueId: queued.queueId,
      collection: record.collection,
      id: record.id,
    };
    this.emit("ark:cloud-record-queued", result);
    return result;
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
    const payload = {
      collection: "predictions",
      id: normalizedRecordId(record?.id),
      data: record,
    };

    if (!this.ready()) {
      return this.queueRecord(payload, "cloud_not_ready");
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

      return this.queueRecord(payload, this.state.lastError);
    }
  }

  async mirrorOutcomeReport(report = {}) {
    if (report?.changed !== true) {
      return {
        savedPredictions: 0,
        savedOutcomes: 0,
        reason: "no_resolved_changes",
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

    if (!this.ready()) {
      records.forEach((record) => {
        this.queueRecord({
          collection: "prediction_outcomes",
          id: normalizedRecordId(record.id),
          data: record,
        }, "cloud_not_ready");
      });
      return {
        savedPredictions: 0,
        savedOutcomes: 0,
        queuedOutcomes: records.length,
        reason: "cloud_not_ready",
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

      records.forEach((record) => {
        this.queueRecord({
          collection: "prediction_outcomes",
          id: normalizedRecordId(record.id),
          data: record,
        }, this.state.lastError);
      });

      return {
        savedPredictions: 0,
        savedOutcomes: 0,
        queuedOutcomes: records.length,
        reason: this.state.lastError,
      };
    }
  }

  async mirrorLearningReport(report) {
    if (!report?.id || report?.executionAllowed !== false) {
      return {
        saved: false,
        reason: "invalid_learning_report",
      };
    }

    const payload = {
      collection: LEARNING_REPORT_COLLECTION,
      id: normalizedRecordId(report.id),
      data: report,
    };

    if (!this.ready()) {
      return this.queueRecord(payload, "cloud_not_ready");
    }

    try {
      await this.cloudRecordWriter(payload);

      this.state.lastError = null;
      const result = {
        saved: true,
        id: payload.id,
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

      return this.queueRecord(payload, this.state.lastError);
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
      .then(async () => {
        if (this.ready()) await this.queueFlusher();
        return this.restore();
      });

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
