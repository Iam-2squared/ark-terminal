import {
  normalizeAIAnalysisSettings,
} from "./ai-analysis-settings.js";

function finiteNumber(
  value,
  fallback = 0,
) {
  const parsed =
    Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : fallback;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function buildAISettingsViewModel(
  settings = {},
) {
  const normalized =
    normalizeAIAnalysisSettings(
      settings,
    );

  return {
    ...normalized,

    capital:
      finiteNumber(
        normalized.capital,
        100000,
      ),

    allocationPercent:
      Math.round(
        normalized.allocation *
        100,
      ),

    weights: {
      technical:
        finiteNumber(
          normalized.weights
            .technical,
          1,
        ),

      ai:
        finiteNumber(
          normalized.weights.ai,
          1,
        ),

      macro:
        finiteNumber(
          normalized.weights
            .macro,
          1,
        ),
    },
  };
}

export function renderAIAnalysisSettings(
  settings = {},
) {
  const view =
    buildAISettingsViewModel(
      settings,
    );

  return `
    <section class="arkAISettingsPanel">
      <header class="arkAISettingsHeader">
        <div>
          <span class="arkAISettingsEyebrow">
            AI ANALYSIS SETTINGS
          </span>

          <h3>
            分析設定
          </h3>
        </div>

        <button
          type="button"
          class="arkAISettingsClose"
          data-ai-settings-close
          aria-label="設定を閉じる"
        >
          ×
        </button>
      </header>

      <div class="arkAISettingsGrid">
        <label>
          <span>運用資金</span>

          <input
            type="number"
            min="0"
            step="1000"
            name="capital"
            value="${escapeHtml(
              view.capital,
            )}"
          >
        </label>

        <label>
          <span>投資配分</span>

          <input
            type="number"
            min="0"
            max="100"
            step="1"
            name="allocationPercent"
            value="${escapeHtml(
              view.allocationPercent,
            )}"
          >
        </label>

        <label>
          <span>売買単位</span>

          <input
            type="number"
            min="1"
            step="1"
            name="lotSize"
            value="${escapeHtml(
              view.lotSize,
            )}"
          >
        </label>

        <label>
          <span>損切り幅（%）</span>

          <input
            type="number"
            min="0"
            max="100"
            step="0.1"
            name="stopPercent"
            value="${escapeHtml(
              view.stopPercent,
            )}"
          >
        </label>

        <label>
          <span>利確幅（%）</span>

          <input
            type="number"
            min="0"
            step="0.1"
            name="targetPercent"
            value="${escapeHtml(
              view.targetPercent,
            )}"
          >
        </label>

        <label>
          <span>最大リスク（%）</span>

          <input
            type="number"
            min="0"
            step="0.1"
            name="maximumRiskPercent"
            value="${escapeHtml(
              view.maximumRiskPercent,
            )}"
          >
        </label>

        <label>
          <span>最低信頼度</span>

          <input
            type="number"
            min="0"
            max="100"
            step="1"
            name="minimumConfidence"
            value="${escapeHtml(
              view.minimumConfidence,
            )}"
          >
        </label>

        <label>
          <span>最低スコア</span>

          <input
            type="number"
            min="0"
            max="100"
            step="1"
            name="minimumScore"
            value="${escapeHtml(
              view.minimumScore,
            )}"
          >
        </label>
      </div>

      <div class="arkAISettingsWeights">
        <h4>分析ウェイト</h4>

        <label>
          <span>Technical</span>

          <input
            type="number"
            min="0"
            step="0.1"
            name="weightTechnical"
            value="${escapeHtml(
              view.weights.technical,
            )}"
          >
        </label>

        <label>
          <span>AI</span>

          <input
            type="number"
            min="0"
            step="0.1"
            name="weightAI"
            value="${escapeHtml(
              view.weights.ai,
            )}"
          >
        </label>

        <label>
          <span>Macro</span>

          <input
            type="number"
            min="0"
            step="0.1"
            name="weightMacro"
            value="${escapeHtml(
              view.weights.macro,
            )}"
          >
        </label>
      </div>

      <div class="arkAISettingsActions">
        <button
          type="button"
          class="arkAISettingsReset"
          data-ai-settings-reset
        >
          初期化
        </button>

        <button
          type="button"
          class="arkAISettingsSave"
          data-ai-settings-save
        >
          保存
        </button>
      </div>

      <p
        class="arkAISettingsMessage"
        data-ai-settings-message
      ></p>
    </section>
  `;
}

export function readSettingsForm(
  container,
) {
  const read =
    (
      name,
      fallback = 0,
    ) => {
      const element =
        container.querySelector(
          `[name="${name}"]`,
        );

      return finiteNumber(
        element?.value,
        fallback,
      );
    };

  return normalizeAIAnalysisSettings({
    capital:
      read(
        "capital",
        100000,
      ),

    allocation:
      read(
        "allocationPercent",
        25,
      ) / 100,

    lotSize:
      read(
        "lotSize",
        100,
      ),

    stopPercent:
      read(
        "stopPercent",
        5,
      ),

    targetPercent:
      read(
        "targetPercent",
        10,
      ),

    maximumRiskPercent:
      read(
        "maximumRiskPercent",
        6,
      ),

    minimumConfidence:
      read(
        "minimumConfidence",
        55,
      ),

    minimumScore:
      read(
        "minimumScore",
        60,
      ),

    weights: {
      technical:
        read(
          "weightTechnical",
          1,
        ),

      ai:
        read(
          "weightAI",
          1,
        ),

      macro:
        read(
          "weightMacro",
          1,
        ),
    },
  });
}

export function mountAIAnalysisSettings({
  documentRef =
    globalThis.document,

  windowRef =
    globalThis.window,
} = {}) {
  if (
    !documentRef ||
    !windowRef
  ) {
    return {
      mounted: false,

      reason:
        "environment_unavailable",
    };
  }

  let container =
    documentRef.querySelector(
      "#arkAISettings",
    );

  if (!container) {
    container =
      documentRef.createElement(
        "section",
      );

    container.id =
      "arkAISettings";

    container.className =
      "arkAISettingsRoot";

    container.hidden =
      true;

    documentRef.body?.appendChild(
      container,
    );
  }

  const settings =
    windowRef
      .ArkAIAnalysisSettings
      ?.get?.() ??
    windowRef
      .__ARK_ANALYSIS_SETTINGS__ ??
    {};

  container.innerHTML =
    renderAIAnalysisSettings(
      settings,
    );

  return {
    mounted: true,
    container,
  };
}

export function connectAIAnalysisSettingsUI({
  documentRef =
    globalThis.document,

  windowRef =
    globalThis.window,
} = {}) {
  if (
    !documentRef ||
    !windowRef
  ) {
    return () => {};
  }

  const mounted =
    mountAIAnalysisSettings({
      documentRef,
      windowRef,
    });

  if (!mounted.mounted) {
    return () => {};
  }

  const container =
    mounted.container;

  const openButton =
    documentRef.querySelector(
      "#aiAnalysisSettingsButton, [data-ai-settings-open]",
    );

  const saveButton =
    container.querySelector(
      "[data-ai-settings-save]",
    );

  const resetButton =
    container.querySelector(
      "[data-ai-settings-reset]",
    );

  const closeButton =
    container.querySelector(
      "[data-ai-settings-close]",
    );

  const message =
    container.querySelector(
      "[data-ai-settings-message]",
    );

  const open = () => {
    container.hidden =
      false;

    container.dataset
      .aiSettingsState =
      "open";
  };

  const close = () => {
    container.hidden =
      true;

    container.dataset
      .aiSettingsState =
      "closed";
  };

  const save = () => {
    const settings =
      readSettingsForm(
        container,
      );

    const updated =
      windowRef
        .ArkAIAnalysisSettings
        ?.update?.(
          settings,
        ) ??
      settings;

    windowRef
      .__ARK_ANALYSIS_SETTINGS__ =
      updated;

    if (message) {
      message.textContent =
        "設定を保存しました";
    }
  };

  const reset = () => {
    const settings =
      windowRef
        .ArkAIAnalysisSettings
        ?.reset?.() ??
      normalizeAIAnalysisSettings();

    container.innerHTML =
      renderAIAnalysisSettings(
        settings,
      );
  };

  openButton?.addEventListener(
    "click",
    open,
  );

  saveButton?.addEventListener(
    "click",
    save,
  );

  resetButton?.addEventListener(
    "click",
    reset,
  );

  closeButton?.addEventListener(
    "click",
    close,
  );

  return () => {
    openButton?.removeEventListener(
      "click",
      open,
    );

    saveButton?.removeEventListener(
      "click",
      save,
    );

    resetButton?.removeEventListener(
      "click",
      reset,
    );

    closeButton?.removeEventListener(
      "click",
      close,
    );
  };
}

export function installAISettingsButton({
  documentRef =
    globalThis.document,
} = {}) {
  if (!documentRef) {
    return null;
  }

  const existing =
    documentRef.querySelector(
      "#aiAnalysisSettingsButton",
    );

  if (existing) {
    return existing;
  }

  const button =
    documentRef.createElement(
      "button",
    );

  button.id =
    "aiAnalysisSettingsButton";

  button.type =
    "button";

  button.className =
    "arkAISettingsOpenButton";

  button.dataset
    .aiSettingsOpen =
    "true";

  button.textContent =
    "分析設定";

  const analysisButton =
    documentRef.querySelector(
      "#aiAnalysisButton",
    );

  const wrapper =
    analysisButton?.parentElement;

  if (
    wrapper &&
    typeof wrapper.appendChild ===
    "function"
  ) {
    wrapper.appendChild(
      button,
    );
  }
  else {
    documentRef.body?.appendChild(
      button,
    );
  }

  return button;
}