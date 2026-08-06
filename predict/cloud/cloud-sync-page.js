import {
  getPredictions,
} from "../backtest/storage.js";

import {
  initCloudSyncController,
} from "./cloud-sync-controller.js";

import {
  selectCloudPredictions,
} from "./prediction-cloud-repository.js";

import {
  loadCloudOperationsStatus,
  saveCloudOperationsStatus,
} from "./cloud-operations-store.js";

import {
  flushSharedOfflineQueue,
  getSharedOfflineQueue,
} from "./queued-cloud-writer.js";

import {
  importSafeBackup,
  serializeSafeBackup,
} from "./safe-backup.js";

function text(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = String(value ?? "--");
}

function dateText(value) {
  if (!value) return "--";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? String(value)
    : parsed.toLocaleString("ja-JP");
}

function updateCounts() {
  const records = getPredictions();
  const eligible = selectCloudPredictions(records);
  const queue = getSharedOfflineQueue();
  const status = loadCloudOperationsStatus();

  text("cloudLocalPredictionCount", `${records.length}件`);
  text("cloudEligiblePredictionCount", `${eligible.length}件`);
  text("cloudOfflineQueueCount", `${queue.count()}件`);
  text("cloudLastSyncAt", dateText(status.lastSyncAt));
  text("cloudLastSuccessAt", dateText(status.lastSuccessAt));
  text(
    "cloudLatencyMs",
    Number.isFinite(Number(status.latencyMs))
      ? `${Number(status.latencyMs)}ms`
      : "--",
  );
}

function downloadJson(content, filename) {
  const blob = new Blob([content], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function showBackupMessage(message, kind = "neutral") {
  const element = document.getElementById("cloudBackupMessage");
  if (!element) return;
  element.textContent = message;
  element.dataset.kind = kind;
}

const controller = initCloudSyncController();
const syncNowButton = document.getElementById("cloudSyncNowButton");
const retryQueueButton = document.getElementById("cloudRetryQueueButton");
const exportButton = document.getElementById("cloudExportBackupButton");
const importInput = document.getElementById("cloudImportBackupInput");
const importMode = document.getElementById("cloudImportMode");

syncNowButton?.addEventListener("click", async () => {
  const startedAt = performance.now();
  saveCloudOperationsStatus({ syncing: true });
  const result = await controller.synchronize();
  const latencyMs = Math.round(performance.now() - startedAt);
  saveCloudOperationsStatus({
    syncing: false,
    lastSyncAt: new Date().toISOString(),
    lastSuccessAt: result?.synchronized ? new Date().toISOString() : undefined,
    lastErrorAt: result?.synchronized ? null : new Date().toISOString(),
    lastError: result?.synchronized ? null : result?.reason ?? "sync_failed",
    latencyMs,
    localCount: getPredictions().length,
    cloudCount: Number(result?.cloudCount) || 0,
  });
  updateCounts();
});

retryQueueButton?.addEventListener("click", async () => {
  const result = await flushSharedOfflineQueue();
  showBackupMessage(
    result.remaining === 0
      ? `再送完了：${result.sent}件`
      : `再送結果：成功${result.sent}件・失敗${result.failed}件・残り${result.remaining}件`,
    result.remaining === 0 ? "success" : "error",
  );
  saveCloudOperationsStatus({
    queueCount: result.remaining,
    lastSyncAt: new Date().toISOString(),
    lastSuccessAt: result.failed === 0 ? new Date().toISOString() : undefined,
    lastError: result.failed === 0 ? null : "queue_flush_failed",
  });
  updateCounts();
});

exportButton?.addEventListener("click", () => {
  try {
    const content = serializeSafeBackup();
    const stamp = new Date().toISOString().slice(0, 10);
    downloadJson(content, `ark-terminal-safe-backup-${stamp}.json`);
    showBackupMessage("安全なJSONバックアップを出力しました。", "success");
  }
  catch (error) {
    showBackupMessage(
      error?.message ?? "バックアップを作成できませんでした。",
      "error",
    );
  }
});

importInput?.addEventListener("change", async () => {
  const file = importInput.files?.[0];
  if (!file) return;

  try {
    const content = await file.text();
    const result = importSafeBackup(content, {
      mode: importMode?.value === "replace" ? "replace" : "merge",
    });
    showBackupMessage(
      `復元完了：予測${result.predictionCount}件・Candidate${result.candidateCount}件・Forward${result.forwardTestCount}件`,
      "success",
    );
    updateCounts();
  }
  catch (error) {
    showBackupMessage(
      error?.message ?? "JSONバックアップを復元できませんでした。",
      "error",
    );
  }
  finally {
    importInput.value = "";
  }
});

window.addEventListener("online", () => {
  saveCloudOperationsStatus({ online: true });
  updateCounts();
});

window.addEventListener("offline", () => {
  saveCloudOperationsStatus({ online: false });
  updateCounts();
});

updateCounts();
