import {
  getPredictions,
  setPredictions,
} from "../backtest/storage.js";

import {
  CloudSyncError,
  connectCloudSync,
  disconnectCloudSync,
  getCloudSyncStatus,
} from "./cloud-sync-client.js";

import {
  loadPredictionStateFromCloud,
  mergePredictionRecords,
  savePredictionToCloud,
  syncPredictionRecordsToCloud,
} from "./prediction-cloud-repository.js";

function findElements(documentRef = globalThis.document) {
  return {
    panel:
      documentRef?.getElementById("cloudSyncPanel") ?? null,
    form:
      documentRef?.getElementById("cloudSyncForm") ?? null,
    secret:
      documentRef?.getElementById("cloudSyncSecret") ?? null,
    connect:
      documentRef?.getElementById("cloudSyncConnectButton") ?? null,
    disconnect:
      documentRef?.getElementById("cloudSyncDisconnectButton") ?? null,
    status:
      documentRef?.getElementById("cloudSyncStatus") ?? null,
    message:
      documentRef?.getElementById("cloudSyncMessage") ?? null,
  };
}

function displayMessage(elements, message, kind = "neutral") {
  if (!elements.message) return;

  elements.message.textContent = message;
  elements.message.dataset.kind = kind;
}

function renderState(elements, state) {
  if (elements.status) {
    elements.status.textContent = state.authenticated
      ? "接続済み"
      : state.configured
        ? "未接続"
        : "未設定";

    elements.status.dataset.state = state.authenticated
      ? "connected"
      : state.configured
        ? "disconnected"
        : "unconfigured";
  }

  if (elements.secret) {
    elements.secret.hidden = state.authenticated;
    elements.secret.disabled = state.loading;
  }

  if (elements.connect) {
    elements.connect.hidden = state.authenticated;
    elements.connect.disabled =
      state.loading ||
      !state.configured;
  }

  if (elements.disconnect) {
    elements.disconnect.hidden = !state.authenticated;
    elements.disconnect.disabled = state.loading;
  }
}

export function initCloudSyncController({
  documentRef = globalThis.document,
  statusProvider = getCloudSyncStatus,
  connectProvider = connectCloudSync,
  disconnectProvider = disconnectCloudSync,
  loadProvider = loadPredictionStateFromCloud,
  syncProvider = syncPredictionRecordsToCloud,
  saveProvider = savePredictionToCloud,
} = {}) {
  const elements = findElements(documentRef);
  const state = {
    configured: false,
    authenticated: false,
    storageConfigured: false,
    loading: false,
  };

  async function refreshStatus() {
    state.loading = true;
    renderState(elements, state);

    try {
      const result = await statusProvider();
      state.configured = result?.configured === true;
      state.authenticated = result?.authenticated === true;
      state.storageConfigured = result?.storageConfigured === true;

      if (!state.configured) {
        displayMessage(
          elements,
          "Vercelの環境変数とクラウド保存先を設定すると利用できます。",
        );
      }
      else if (state.authenticated) {
        displayMessage(
          elements,
          "予測履歴は端末内とクラウドへ二重保存されます。",
          "success",
        );
      }
      else {
        displayMessage(
          elements,
          "同期パスフレーズは端末へ保存されません。",
        );
      }

      return result;
    }
    catch (error) {
      state.configured = false;
      state.authenticated = false;
      displayMessage(
        elements,
        error?.message ??
        "クラウド保存の状態を確認できませんでした。",
        "error",
      );
      return null;
    }
    finally {
      state.loading = false;
      renderState(elements, state);
    }
  }

  async function synchronize() {
    if (!state.authenticated) {
      return {
        synchronized: false,
        reason: "not_authenticated",
      };
    }

    state.loading = true;
    renderState(elements, state);
    displayMessage(
      elements,
      "端末とクラウドの予測履歴を同期しています…",
    );

    try {
      const localRecords = getPredictions();
      const cloud = await loadProvider();
      const merged = mergePredictionRecords(
        localRecords,
        cloud.predictions,
      );

      setPredictions(merged);

      const saved = await syncProvider(merged);

      displayMessage(
        elements,
        `同期完了：予測${saved.savedPredictions}件・結果${saved.savedOutcomes}件`,
        "success",
      );

      return {
        synchronized: true,
        localCount: localRecords.length,
        cloudCount: cloud.predictions.length,
        mergedCount: merged.length,
        ...saved,
      };
    }
    catch (error) {
      if (error instanceof CloudSyncError && error.status === 401) {
        state.authenticated = false;
      }

      displayMessage(
        elements,
        error?.message ??
        "クラウド同期に失敗しました。ローカル保存は継続しています。",
        "error",
      );

      return {
        synchronized: false,
        reason:
          error?.code ??
          "sync_failed",
      };
    }
    finally {
      state.loading = false;
      renderState(elements, state);
    }
  }

  async function connect(secret) {
    state.loading = true;
    renderState(elements, state);

    try {
      await connectProvider(secret);
      state.authenticated = true;
      state.configured = true;
      state.storageConfigured = true;

      if (elements.secret) {
        elements.secret.value = "";
      }

      return synchronize();
    }
    catch (error) {
      state.authenticated = false;
      displayMessage(
        elements,
        error?.message ??
        "クラウド保存へ接続できませんでした。",
        "error",
      );

      return {
        synchronized: false,
        reason:
          error?.code ??
          "connect_failed",
      };
    }
    finally {
      state.loading = false;
      renderState(elements, state);
    }
  }

  async function disconnect() {
    state.loading = true;
    renderState(elements, state);

    try {
      await disconnectProvider();
    }
    finally {
      state.authenticated = false;
      state.loading = false;
      renderState(elements, state);
      displayMessage(
        elements,
        "クラウド接続を切断しました。ローカル保存は継続します。",
      );
    }
  }

  async function mirrorPrediction(record) {
    if (!state.authenticated) {
      return {
        saved: false,
        reason: "not_authenticated",
      };
    }

    try {
      const result = await saveProvider(record);

      if (result.saved) {
        displayMessage(
          elements,
          "今回の予測をクラウドにも保存しました。",
          "success",
        );
      }

      return result;
    }
    catch (error) {
      if (error instanceof CloudSyncError && error.status === 401) {
        state.authenticated = false;
        renderState(elements, state);
      }

      displayMessage(
        elements,
        "クラウド保存に失敗しました。端末内には保存されています。",
        "error",
      );

      return {
        saved: false,
        reason:
          error?.code ??
          "cloud_save_failed",
      };
    }
  }

  async function mirrorRecords(records) {
    if (!state.authenticated) {
      return {
        savedPredictions: 0,
        savedOutcomes: 0,
        reason: "not_authenticated",
      };
    }

    try {
      return await syncProvider(records);
    }
    catch (error) {
      if (error instanceof CloudSyncError && error.status === 401) {
        state.authenticated = false;
        renderState(elements, state);
      }

      return {
        savedPredictions: 0,
        savedOutcomes: 0,
        reason:
          error?.code ??
          "cloud_save_failed",
      };
    }
  }

  elements.form?.addEventListener("submit", (event) => {
    event.preventDefault();
    void connect(elements.secret?.value ?? "");
  });

  elements.disconnect?.addEventListener("click", () => {
    void disconnect();
  });

  void refreshStatus().then(() => {
    if (state.authenticated) {
      void synchronize();
    }
  });

  return {
    connect,
    disconnect,
    mirrorPrediction,
    mirrorRecords,
    refreshStatus,
    state,
    synchronize,
  };
}

export const CloudSyncControllerInternals = {
  displayMessage,
  findElements,
  renderState,
};
