import {
  getPredictions,
  setPredictions,
} from "../backtest/storage.js";

import {
  getCloudSyncStatus,
  saveCloudRecord,
} from "./cloud-sync-client.js";

import {
  loadLearningArchiveFromCloud,
} from "./learning-cloud-repository.js";

import {
  OfflineSyncQueue,
} from "./offline-sync-queue.js";

import {
  buildSafeBackup,
  mergeRecordsByIdentity,
  validateSafeBackup,
} from "./safe-backup-repository.js";

const LEARNING_ARCHIVE_LOCAL_KEY = "ark.learning-cloud-archive.readonly.v1";
const OPERATIONS_META_KEY = "ark.operations.meta.v1";

function $(id) {
  return document.getElementById(id);
}

function text(id, value) {
  const element = $(id);
  if (element) element.textContent = String(value ?? "--");
}

function formatTime(value) {
  const timestamp = Date.parse(value ?? "");
  if (!Number.isFinite(timestamp)) return "--";
  return new Intl.DateTimeFormat("ja-JP", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(timestamp));
}

function readJsonStorage(key, fallback) {
  try {
    const raw = globalThis.localStorage?.getItem?.(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function writeJsonStorage(key, value) {
  globalThis.localStorage?.setItem?.(key, JSON.stringify(value));
}

function emptyArchive() {
  return {
    candidates: [],
    forwardTests: [],
    modelVersions: [],
    restoredAt: null,
    readOnly: true,
    appliedToRuntime: false,
  };
}

function archiveData(record) {
  return record?.data ?? record ?? {};
}

function localLearningArchive() {
  return readJsonStorage(LEARNING_ARCHIVE_LOCAL_KEY, emptyArchive());
}

function saveLocalLearningArchive(archive) {
  writeJsonStorage(LEARNING_ARCHIVE_LOCAL_KEY, {
    ...emptyArchive(),
    ...archive,
    readOnly: true,
    appliedToRuntime: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    brokerWriteAllowed: false,
  });
}

function resolvedPredictions(records) {
  return records.filter((record) =>
    record?.status === "RESOLVED" ||
    record?.resolvedAt ||
    record?.actualPrice !== undefined ||
    record?.hit !== undefined,
  );
}

function pendingReviews(archive) {
  return archive.candidates
    .map(archiveData)
    .filter((candidate) => [
      "READY_FOR_REVIEW",
      "READY_FOR_HUMAN_REVIEW",
      "PROPOSED_FOR_VALIDATION",
    ].includes(String(candidate?.status ?? "").toUpperCase()));
}

function renderList(targetId, rows, emptyMessage, formatter) {
  const target = $(targetId);
  if (!target) return;
  target.replaceChildren();

  if (!rows.length) {
    const item = document.createElement("div");
    item.className = "operationsListItem";
    item.textContent = emptyMessage;
    target.append(item);
    return;
  }

  rows.slice(0, 8).forEach((row) => {
    const item = document.createElement("div");
    item.className = "operationsListItem";
    const output = formatter(row);
    const title = document.createElement("strong");
    title.textContent = output.title;
    const subtitle = document.createElement("span");
    subtitle.textContent = output.subtitle;
    const meta = document.createElement("small");
    meta.textContent = output.meta;
    item.append(title, subtitle, meta);
    target.append(item);
  });
}

function downloadJson(payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `ark-terminal-backup-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

const queue = new OfflineSyncQueue({
  sender: saveCloudRecord,
});

let currentStatus = null;
let currentArchive = localLearningArchive();
let lastFlushAt = readJsonStorage(OPERATIONS_META_KEY, {}).lastFlushAt ?? null;

function renderQueue() {
  const rows = queue.list();
  const failed = rows.filter((item) => Number(item.attempts) > 0);
  text("cloudQueueCount", `${rows.length}件`);
  text("queuePendingCount", `${rows.length}件`);
  text("queueFailedCount", `${failed.length}件`);
  text("queueLastFlushAt", formatTime(lastFlushAt));
  text("queueOperationsBadge", `${rows.length}件`);

  renderList(
    "queuePreview",
    rows,
    "再送待ちデータはありません。",
    (item) => ({
      title: `${item.collection} / ${item.id}`,
      subtitle: `試行 ${Number(item.attempts) || 0}回`,
      meta: `${formatTime(item.queuedAt)}${item.lastError ? `・${item.lastError}` : ""}`,
    }),
  );
}

function renderLearning() {
  const predictions = getPredictions();
  const resolved = resolvedPredictions(predictions);
  const candidates = currentArchive.candidates ?? [];
  const forwardTests = currentArchive.forwardTests ?? [];
  const modelVersions = currentArchive.modelVersions ?? [];
  const reviews = pendingReviews(currentArchive);

  text("learningPredictionCount", `${predictions.length}件`);
  text("learningResolvedCount", `${resolved.length}件`);
  text("learningCandidateCount", `${candidates.length}件`);
  text("learningForwardCount", `${forwardTests.length}件`);
  text("learningModelCount", `${modelVersions.length}件`);
  text("learningReviewCount", `${reviews.length}件`);
  text(
    "learningOperationsBadge",
    currentArchive.restoredAt ? `Cloud ${formatTime(currentArchive.restoredAt)}` : "Local",
  );

  renderList(
    "learningCandidateList",
    candidates.map(archiveData),
    "Candidate履歴はまだありません。",
    (candidate) => ({
      title: candidate.version ?? candidate.id ?? "Candidate",
      subtitle: candidate.status ?? "UNKNOWN",
      meta: `作成 ${formatTime(candidate.updatedAt ?? candidate.createdAt)}`,
    }),
  );

  const timeline = [
    ...forwardTests.map((entry) => ({ type: "Forward", ...archiveData(entry) })),
    ...modelVersions.map((entry) => ({ type: "Model", ...archiveData(entry) })),
  ].sort((left, right) =>
    Date.parse(right.recordedAt ?? right.generatedAt ?? right.updatedAt ?? 0) -
    Date.parse(left.recordedAt ?? left.generatedAt ?? left.updatedAt ?? 0),
  );

  renderList(
    "learningTimeline",
    timeline,
    "Forward・モデル監査履歴はまだありません。",
    (entry) => ({
      title: `${entry.type}: ${entry.action ?? entry.status ?? entry.version ?? "Record"}`,
      subtitle: entry.version ?? entry.candidateId ?? entry.id ?? "--",
      meta: formatTime(entry.recordedAt ?? entry.generatedAt ?? entry.updatedAt),
    }),
  );
}

function renderCloudStatus(status) {
  currentStatus = status;
  const configured = status?.configured === true;
  const storageConfigured = status?.storageConfigured === true;
  const authenticated = status?.authenticated === true;

  text("cloudConnectionState", authenticated ? "接続済み" : configured ? "未接続" : "未設定");
  text("cloudStorageState", storageConfigured ? "Ready" : "未設定");
  text("cloudLastCheckedAt", formatTime(new Date().toISOString()));
  text(
    "cloudOperationsBadge",
    authenticated && storageConfigured ? "Connected" : configured ? "Waiting" : "Disabled",
  );
  text(
    "cloudOperationsMessage",
    authenticated && storageConfigured
      ? "クラウド保存を利用できます。"
      : "ローカル保存とQueueは継続します。接続後に再送できます。",
  );

  const healthBadge = $("operationsHealthBadge");
  if (healthBadge) {
    healthBadge.className = "operationsHealthBadge";
    if (authenticated && storageConfigured && queue.count() === 0) {
      healthBadge.classList.add("healthy");
      healthBadge.textContent = "Healthy";
      text("operationsHealthMessage", "Cloud Syncとローカル保存は正常です。");
    } else if (queue.count() > 0 || configured) {
      healthBadge.classList.add("warning");
      healthBadge.textContent = "Attention";
      text("operationsHealthMessage", "ローカル保存は正常です。クラウド接続または再送待ちがあります。");
    } else {
      healthBadge.classList.add("warning");
      healthBadge.textContent = "Local Only";
      text("operationsHealthMessage", "クラウド未設定ですが、ローカル機能は利用できます。");
    }
  }
}

async function refreshAll() {
  text("cloudOperationsMessage", "状態を確認しています。");

  try {
    const status = await getCloudSyncStatus();
    renderCloudStatus(status);

    if (
      status?.configured === true &&
      status?.storageConfigured === true &&
      status?.authenticated === true
    ) {
      try {
        const archive = await loadLearningArchiveFromCloud();
        currentArchive = {
          ...archive,
          readOnly: true,
          appliedToRuntime: false,
        };
        saveLocalLearningArchive(currentArchive);
      } catch {
        currentArchive = localLearningArchive();
      }
    }
  } catch {
    renderCloudStatus(null);
  }

  renderQueue();
  renderLearning();
}

$("refreshOperationsButton")?.addEventListener("click", refreshAll);

$("flushQueueButton")?.addEventListener("click", async () => {
  text("cloudOperationsMessage", "Queueを再送しています。");
  const result = await queue.flush();
  lastFlushAt = new Date().toISOString();
  writeJsonStorage(OPERATIONS_META_KEY, { lastFlushAt });
  text(
    "cloudOperationsMessage",
    `再送完了：成功${result.sent}件・失敗${result.failed}件・残り${result.remaining}件`,
  );
  renderQueue();
  renderCloudStatus(currentStatus);
});

$("clearQueueButton")?.addEventListener("click", () => {
  const removed = queue.clear();
  text("cloudOperationsMessage", `${removed}件の再送待ちを削除しました。`);
  renderQueue();
  renderCloudStatus(currentStatus);
});

$("exportBackupButton")?.addEventListener("click", () => {
  try {
    const predictions = getPredictions();
    const backup = buildSafeBackup({
      predictions,
      predictionOutcomes: resolvedPredictions(predictions),
      candidateModels: (currentArchive.candidates ?? []).map(archiveData),
      forwardTestResults: (currentArchive.forwardTests ?? []).map(archiveData),
      modelVersions: (currentArchive.modelVersions ?? []).map(archiveData),
    });
    downloadJson(backup);
    text("backupOperationsMessage", "安全なバックアップJSONを出力しました。");
  } catch (error) {
    text("backupOperationsMessage", `出力を中止しました：${error?.message ?? "UNKNOWN_ERROR"}`);
  }
});

$("importBackupButton")?.addEventListener("click", async () => {
  const file = $("importBackupInput")?.files?.[0];
  if (!file) {
    text("backupOperationsMessage", "JSONファイルを選択してください。");
    return;
  }

  try {
    const parsed = JSON.parse(await file.text());
    const backup = validateSafeBackup(parsed);
    const mergedPredictions = mergeRecordsByIdentity(
      getPredictions(),
      backup.collections.predictions,
    );
    setPredictions(mergedPredictions);

    currentArchive = {
      ...emptyArchive(),
      restoredAt: new Date().toISOString(),
      candidates: backup.collections.candidate_models.map((data) => ({ data })),
      forwardTests: backup.collections.forward_test_results.map((data) => ({ data })),
      modelVersions: backup.collections.model_versions.map((data) => ({ data })),
      readOnly: true,
      appliedToRuntime: false,
    };
    saveLocalLearningArchive(currentArchive);
    renderLearning();
    text(
      "backupOperationsMessage",
      `復元しました：予測${backup.counts.predictions}件・Candidate${backup.counts.candidate_models}件・Forward${backup.counts.forward_test_results}件`,
    );
  } catch (error) {
    text("backupOperationsMessage", `復元を拒否しました：${error?.message ?? "INVALID_BACKUP"}`);
  }
});

globalThis.addEventListener?.("online", async () => {
  await queue.flush();
  lastFlushAt = new Date().toISOString();
  writeJsonStorage(OPERATIONS_META_KEY, { lastFlushAt });
  await refreshAll();
});

await refreshAll();
