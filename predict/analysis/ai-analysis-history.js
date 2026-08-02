const DEFAULT_STORAGE_KEY =
  "ark-ai-analysis-history";

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

function createHistoryId() {
  return (
    globalThis.crypto
      ?.randomUUID?.() ??
    [
      "analysis",
      Date.now()
        .toString(36),
      Math.random()
        .toString(36)
        .slice(2, 10),
    ].join("-")
  );
}

export function createAnalysisHistoryEntry(
  result = {},
) {
  return {
    id:
      result.id ??
      createHistoryId(),

    createdAt:
      result.createdAt ??
      result.generatedAt ??
      new Date()
        .toISOString(),

    symbol:
      result.symbol ??
      null,

    action:
      result.action ??
      "HOLD",

    score:
      finiteNumber(
        result.score,
        50,
      ),

    confidence:
      finiteNumber(
        result.confidence,
        0,
      ),

    agreementRate:
      finiteNumber(
        result.agreementRate,
        0,
      ),

    executable:
      result.executable === true,

    shares:
      finiteNumber(
        result.shares,
        0,
      ),

    entryPrice:
      finiteNumber(
        result.entryPrice,
        0,
      ),

    stopPrice:
      finiteNumber(
        result.stopPrice,
        0,
      ),

    targetPrice:
      finiteNumber(
        result.targetPrice,
        0,
      ),

    estimatedCost:
      finiteNumber(
        result.estimatedCost,
        0,
      ),

    buyFactors:
      Array.isArray(
        result.buyFactors,
      )
        ? [...result.buyFactors]
        : [],

    riskFactors:
      Array.isArray(
        result.riskFactors,
      )
        ? [...result.riskFactors]
        : [],
  };
}

export function appendAnalysisHistory({
  history = [],
  result = {},
  limit = 100,
} = {}) {
  const safeHistory =
    Array.isArray(history)
      ? history
      : [];

  const entry =
    createAnalysisHistoryEntry(
      result,
    );

  const safeLimit =
    Math.max(
      1,
      Math.floor(
        finiteNumber(
          limit,
          100,
        ),
      ),
    );

  const merged = [
    entry,
    ...safeHistory.filter(
      (item) =>
        item.id !== entry.id,
    ),
  ];

  return merged
    .sort(
      (
        first,
        second,
      ) =>
        new Date(
          second.createdAt,
        ) -
        new Date(
          first.createdAt,
        ),
    )
    .slice(
      0,
      safeLimit,
    );
}

export function summarizeAnalysisHistory(
  history = [],
) {
  const safeHistory =
    Array.isArray(history)
      ? history
      : [];

  if (
    safeHistory.length === 0
  ) {
    return {
      total: 0,
      executableCount: 0,
      averageScore: 0,
      averageConfidence: 0,
      latest: null,
    };
  }

  const executableCount =
    safeHistory.filter(
      (item) =>
        item.executable === true,
    ).length;

  const averageScore =
    safeHistory.reduce(
      (sum, item) =>
        sum +
        finiteNumber(
          item.score,
        ),
      0,
    ) /
    safeHistory.length;

  const averageConfidence =
    safeHistory.reduce(
      (sum, item) =>
        sum +
        finiteNumber(
          item.confidence,
        ),
      0,
    ) /
    safeHistory.length;

  return {
    total:
      safeHistory.length,

    executableCount,

    averageScore:
      Math.round(
        averageScore * 100,
      ) / 100,

    averageConfidence:
      Math.round(
        averageConfidence * 100,
      ) / 100,

    latest:
      safeHistory[0] ??
      null,
  };
}

export function readAnalysisHistory({
  storage =
    globalThis.localStorage,
  key =
    DEFAULT_STORAGE_KEY,
} = {}) {
  if (
    !storage ||
    typeof storage.getItem !==
      "function"
  ) {
    return [];
  }

  try {
    const raw =
      storage.getItem(key);

    const parsed =
      raw
        ? JSON.parse(raw)
        : [];

    return Array.isArray(parsed)
      ? parsed
      : [];
  }
  catch {
    return [];
  }
}

export function saveAnalysisHistory({
  history = [],
  storage =
    globalThis.localStorage,
  key =
    DEFAULT_STORAGE_KEY,
} = {}) {
  const safeHistory =
    Array.isArray(history)
      ? history
      : [];

  if (
    storage &&
    typeof storage.setItem ===
      "function"
  ) {
    storage.setItem(
      key,
      JSON.stringify(
        safeHistory,
      ),
    );
  }

  return safeHistory;
}

export class AIAnalysisHistoryStore {
  constructor({
    storage =
      globalThis.localStorage,

    key =
      DEFAULT_STORAGE_KEY,

    limit = 100,
  } = {}) {
    this.storage =
      storage;

    this.key =
      key;

    this.limit =
      limit;

    this.history =
      readAnalysisHistory({
        storage,
        key,
      });
  }

  add(result = {}) {
    this.history =
      appendAnalysisHistory({
        history:
          this.history,

        result,

        limit:
          this.limit,
      });

    saveAnalysisHistory({
      history:
        this.history,

      storage:
        this.storage,

      key:
        this.key,
    });

    return this.history[0];
  }

  all() {
    return [
      ...this.history,
    ];
  }

  summary() {
    return summarizeAnalysisHistory(
      this.history,
    );
  }

  clear() {
    this.history = [];

    saveAnalysisHistory({
      history: [],
      storage:
        this.storage,
      key:
        this.key,
    });

    return [];
  }
}

export function connectAIAnalysisHistory({
  eventTarget =
    globalThis.window,

  storage =
    globalThis.localStorage,

  limit = 100,
} = {}) {
  if (!eventTarget) {
    return {
      store:
        new AIAnalysisHistoryStore({
          storage,
          limit,
        }),

      cleanup() {},
    };
  }

  const store =
    new AIAnalysisHistoryStore({
      storage,
      limit,
    });

  const completeHandler =
    (event) => {
      store.add(
        event?.detail ?? {},
      );

      eventTarget
        .__ARK_ANALYSIS_HISTORY__ =
        store.all();
    };

  eventTarget.addEventListener(
    "ark:ai-analysis-complete",
    completeHandler,
  );

  eventTarget
    .__ARK_ANALYSIS_HISTORY__ =
    store.all();

  return {
    store,

    cleanup() {
      eventTarget.removeEventListener(
        "ark:ai-analysis-complete",
        completeHandler,
      );
    },
  };
}

export const AIAnalysisHistoryInternals = {
  DEFAULT_STORAGE_KEY,
  finiteNumber,
};