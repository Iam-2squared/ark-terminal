import {
  CloudSyncError,
  getCloudSyncStatus,
} from "./cloud-sync-client.js";

import {
  loadLearningArchiveFromCloud,
  saveCandidateArchiveToCloud,
  saveForwardValidationArchiveToCloud,
  saveModelVersionArchiveToCloud,
} from "./learning-cloud-repository.js";

export const LEARNING_CLOUD_AUTO_SYNC_VERSION =
  "learning-cloud-auto-sync-v1";

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

function claimsExecutionPermission(value = {}) {
  const safety = value?.safety ?? {};

  return [
    value?.automaticPromotionAllowed,
    value?.runtimeActivationAllowed,
    value?.productionUpdateAllowed,
    value?.brokerWriteAllowed,
    value?.liveTradingAllowed,
    value?.liveBrokerAllowed,
    safety?.automaticPromotionAllowed,
    safety?.runtimeActivationAllowed,
    safety?.productionUpdateAllowed,
    safety?.brokerWriteAllowed,
    safety?.liveTradingAllowed,
    safety?.liveBrokerAllowed,
  ].some((permission) => permission === true);
}

function archiveIsSafe(archive = {}) {
  if (
    archive?.readOnly !== true ||
    archive?.appliedToRuntime !== false ||
    archive?.automaticPromotionAllowed !== false ||
    archive?.productionUpdateAllowed !== false ||
    archive?.brokerWriteAllowed !== false
  ) {
    return false;
  }

  const entries = [
    ...(Array.isArray(archive?.candidates) ? archive.candidates : []),
    ...(Array.isArray(archive?.forwardTests) ? archive.forwardTests : []),
    ...(Array.isArray(archive?.modelVersions) ? archive.modelVersions : []),
  ];

  return entries.every((entry) => {
    const data = entry?.data ?? entry;
    return !claimsExecutionPermission(data);
  });
}

export class LearningCloudAutoSyncController {
  constructor({
    statusProvider = getCloudSyncStatus,
    archiveLoader = loadLearningArchiveFromCloud,
    candidateWriter = saveCandidateArchiveToCloud,
    forwardWriter = saveForwardValidationArchiveToCloud,
    modelWriter = saveModelVersionArchiveToCloud,
    eventTarget = globalThis.window ?? null,
  } = {}) {
    for (const [name, value] of Object.entries({
      statusProvider,
      archiveLoader,
      candidateWriter,
      forwardWriter,
      modelWriter,
    })) {
      if (typeof value !== "function") {
        throw new TypeError(`${name} must be a function.`);
      }
    }

    this.statusProvider = statusProvider;
    this.archiveLoader = archiveLoader;
    this.candidateWriter = candidateWriter;
    this.forwardWriter = forwardWriter;
    this.modelWriter = modelWriter;
    this.eventTarget = eventTarget;
    this.activeRestore = null;
    this.activeStatusRefresh = null;

    this.state = {
      version: LEARNING_CLOUD_AUTO_SYNC_VERSION,
      configured: false,
      storageConfigured: false,
      authenticated: false,
      started: false,
      archive: null,
      lastRestoreAt: null,
      lastError: null,
    };

    this.handleCandidate = (event) => {
      void this.mirrorCandidate(event?.detail);
    };
    this.handleForward = (event) => {
      void this.mirrorForwardValidation(event?.detail);
    };
    this.handleModel = (event) => {
      void this.mirrorModelVersion(event?.detail);
    };
    this.handleOnline = () => {
      void this.refreshStatus().then(() => this.restore());
    };
  }

  emit(name, detail) {
    this.eventTarget?.dispatchEvent?.(
      eventWithDetail(name, {
        version: LEARNING_CLOUD_AUTO_SYNC_VERSION,
        ...detail,
      }),
    );
  }

  ready() {
    return cloudReady(this.state);
  }

  async refreshStatus() {
    if (this.activeStatusRefresh) return this.activeStatusRefresh;

    this.activeStatusRefresh = Promise.resolve()
      .then(async () => {
        const status = await this.statusProvider();
        this.state.configured = status?.configured === true;
        this.state.storageConfigured = status?.storageConfigured === true;
        this.state.authenticated = status?.authenticated === true;
        this.state.lastError = null;
        return status;
      })
      .catch((error) => {
        this.state.authenticated = false;
        this.state.lastError = error?.code ?? "learning_cloud_status_failed";
        return null;
      })
      .finally(() => {
        this.activeStatusRefresh = null;
      });

    return this.activeStatusRefresh;
  }

  async ensureReady() {
    if (this.ready()) return true;
    await this.refreshStatus();
    return this.ready();
  }

  handleCloudError(error, fallbackCode) {
    if (error instanceof CloudSyncError && error.status === 401) {
      this.state.authenticated = false;
    }

    this.state.lastError = error?.code ?? fallbackCode;
    return this.state.lastError;
  }

  async restore() {
    if (this.activeRestore) return this.activeRestore;

    this.activeRestore = Promise.resolve()
      .then(async () => {
        if (!(await this.ensureReady())) {
          return {
            restored: false,
            reason: "cloud_not_ready",
            appliedToRuntime: false,
          };
        }

        const archive = await this.archiveLoader();

        if (!archiveIsSafe(archive)) {
          throw new Error("UNSAFE_LEARNING_ARCHIVE_RESTORE_REJECTED");
        }

        this.state.archive = archive;
        this.state.lastRestoreAt = new Date().toISOString();
        this.state.lastError = null;

        const result = {
          restored: true,
          readOnly: true,
          appliedToRuntime: false,
          candidateCount: archive.candidates?.length ?? 0,
          forwardTestCount: archive.forwardTests?.length ?? 0,
          modelVersionCount: archive.modelVersions?.length ?? 0,
          restoredAt: this.state.lastRestoreAt,
        };

        this.emit("ark:learning-cloud-archive-restored", {
          ...result,
          archive,
        });

        return result;
      })
      .catch((error) => {
        const reason = this.handleCloudError(
          error,
          "learning_cloud_restore_failed",
        );
        const result = {
          restored: false,
          reason,
          appliedToRuntime: false,
        };
        this.emit("ark:learning-cloud-sync-error", result);
        return result;
      })
      .finally(() => {
        this.activeRestore = null;
      });

    return this.activeRestore;
  }

  async mirrorCandidate(detail = {}) {
    if (!(await this.ensureReady())) {
      return { saved: false, reason: "cloud_not_ready" };
    }

    try {
      const result = await this.candidateWriter({
        candidate: detail?.candidate,
        action: detail?.action,
      });
      this.state.lastError = null;
      this.emit("ark:learning-cloud-candidate-saved", result);
      return result;
    }
    catch (error) {
      return {
        saved: false,
        reason: this.handleCloudError(
          error,
          "learning_cloud_candidate_save_failed",
        ),
      };
    }
  }

  async mirrorForwardValidation(detail = {}) {
    if (!(await this.ensureReady())) {
      return { saved: false, reason: "cloud_not_ready" };
    }

    try {
      const result = await this.forwardWriter({
        result: detail?.result,
        candidateId: detail?.candidateId,
      });
      this.state.lastError = null;
      this.emit("ark:learning-cloud-forward-saved", result);
      return result;
    }
    catch (error) {
      return {
        saved: false,
        reason: this.handleCloudError(
          error,
          "learning_cloud_forward_save_failed",
        ),
      };
    }
  }

  async mirrorModelVersion(detail = {}) {
    if (!(await this.ensureReady())) {
      return { saved: false, reason: "cloud_not_ready" };
    }

    try {
      const result = await this.modelWriter(detail);
      this.state.lastError = null;
      this.emit("ark:learning-cloud-model-version-saved", result);
      return result;
    }
    catch (error) {
      return {
        saved: false,
        reason: this.handleCloudError(
          error,
          "learning_cloud_model_version_save_failed",
        ),
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
          appliedToRuntime: false,
        }),
      };
    }

    this.state.started = true;
    this.eventTarget?.addEventListener?.(
      "ark:candidate-state-changed",
      this.handleCandidate,
    );
    this.eventTarget?.addEventListener?.(
      "ark:forward-validation-recorded",
      this.handleForward,
    );
    this.eventTarget?.addEventListener?.(
      "ark:model-version-audit",
      this.handleModel,
    );
    this.eventTarget?.addEventListener?.(
      "online",
      this.handleOnline,
    );

    const ready = this.refreshStatus().then(() => this.restore());

    return {
      started: true,
      reused: false,
      controller: this,
      ready,
    };
  }

  stop() {
    this.eventTarget?.removeEventListener?.(
      "ark:candidate-state-changed",
      this.handleCandidate,
    );
    this.eventTarget?.removeEventListener?.(
      "ark:forward-validation-recorded",
      this.handleForward,
    );
    this.eventTarget?.removeEventListener?.(
      "ark:model-version-audit",
      this.handleModel,
    );
    this.eventTarget?.removeEventListener?.(
      "online",
      this.handleOnline,
    );
    this.state.started = false;
    return { stopped: true };
  }

  getArchive() {
    if (!this.state.archive) return null;
    return JSON.parse(JSON.stringify(this.state.archive));
  }
}

let activeController = null;

export function initLearningCloudAutoSync(options = {}) {
  activeController?.stop();
  activeController = new LearningCloudAutoSyncController(options);
  const started = activeController.start();

  return {
    controller: activeController,
    ready: started.ready,
  };
}

export function stopLearningCloudAutoSync() {
  activeController?.stop();
  activeController = null;
}

export const LearningCloudAutoSyncInternals = Object.freeze({
  archiveIsSafe,
  claimsExecutionPermission,
  cloudReady,
  eventWithDetail,
});

export default LearningCloudAutoSyncController;
