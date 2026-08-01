import {
  STORAGE_KEYS,
} from "../config.js";

export const TRADE_MEMORY_VERSION =
  "ark-trade-memory-v1";

const DATABASE_NAME =
  "arkTradeMemory";

const DATABASE_VERSION = 1;
const RECORD_STORE = "tradeGateRecords";
const MAX_LOCAL_RECORDS = 2_000;

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function createId() {
  if (
    globalThis.crypto &&
    typeof globalThis.crypto.randomUUID ===
      "function"
  ) {
    return globalThis.crypto.randomUUID();
  }

  return (
    `${Date.now()}-` +
    Math.random()
      .toString(36)
      .slice(2)
  );
}

function storageAvailable() {
  return Boolean(
    globalThis.localStorage,
  );
}

export function getTradeMemory() {
  if (!storageAvailable()) {
    return [];
  }

  try {
    const records =
      JSON.parse(
        globalThis.localStorage.getItem(
          STORAGE_KEYS.tradeMemory,
        ),
      );

    return Array.isArray(records)
      ? records
      : [];
  } catch {
    return [];
  }
}

function openTradeMemoryDatabase() {
  if (!globalThis.indexedDB) {
    return Promise.resolve(null);
  }

  return new Promise(
    (resolve, reject) => {
      const request =
        globalThis.indexedDB.open(
          DATABASE_NAME,
          DATABASE_VERSION,
        );

      request.onupgradeneeded = () => {
        const database =
          request.result;

        if (
          !database.objectStoreNames
            .contains(RECORD_STORE)
        ) {
          const store =
            database.createObjectStore(
              RECORD_STORE,
              {
                keyPath: "id",
              },
            );

          store.createIndex(
            "createdAt",
            "createdAt",
          );

          store.createIndex(
            "symbol",
            "symbol",
          );

          store.createIndex(
            "decision",
            "decision",
          );

          store.createIndex(
            "status",
            "status",
          );

          store.createIndex(
            "candidateKey",
            "candidateKey",
            {
              unique: false,
            },
          );
        }
      };

      request.onsuccess = () =>
        resolve(request.result);

      request.onerror = () =>
        reject(request.error);
    },
  );
}

async function persistTradeMemory(
  records,
) {
  const database =
    await openTradeMemoryDatabase();

  if (!database) {
    return;
  }

  await new Promise(
    (resolve, reject) => {
      const transaction =
        database.transaction(
          RECORD_STORE,
          "readwrite",
        );

      const store =
        transaction.objectStore(
          RECORD_STORE,
        );

      records.forEach(
        (record) =>
          store.put(record),
      );

      transaction.oncomplete =
        resolve;

      transaction.onerror = () =>
        reject(transaction.error);
    },
  );

  database.close();
}

async function indexedTradeMemory() {
  const database =
    await openTradeMemoryDatabase();

  if (!database) {
    return [];
  }

  const records =
    await new Promise(
      (resolve, reject) => {
        const transaction =
          database.transaction(
            RECORD_STORE,
            "readonly",
          );

        const request =
          transaction
            .objectStore(
              RECORD_STORE,
            )
            .getAll();

        request.onsuccess = () =>
          resolve(
            request.result || [],
          );

        request.onerror = () =>
          reject(request.error);
      },
    );

  database.close();

  return records;
}

export function setTradeMemory(
  records,
) {
  const normalized =
    Array.isArray(records)
      ? records
      : [];

  const limited =
    normalized.slice(
      -MAX_LOCAL_RECORDS,
    );

  if (storageAvailable()) {
    globalThis.localStorage.setItem(
      STORAGE_KEYS.tradeMemory,
      JSON.stringify(limited),
    );
  }

  void persistTradeMemory(
    normalized,
  ).catch((error) => {
    console.warn(
      "Trade Memory archive:",
      error,
    );
  });

  return limited;
}

export async function getTradeMemoryAsync() {
  const localRecords =
    getTradeMemory();

  try {
    const archived =
      await indexedTradeMemory();

    const merged =
      new Map();

    [
      ...archived,
      ...localRecords,
    ].forEach((record) => {
      if (record?.id) {
        merged.set(
          record.id,
          record,
        );
      }
    });

    const records =
      Array.from(
        merged.values(),
      ).sort(
        (first, second) =>
          new Date(
            first.createdAt,
          ) -
          new Date(
            second.createdAt,
          ),
      );

    if (
      archived.length <
      localRecords.length
    ) {
      void persistTradeMemory(
        localRecords,
      );
    }

    return records;
  } catch (error) {
    console.warn(
      "Trade Memory archive:",
      error,
    );

    return localRecords;
  }
}

function roundCandidatePrice(
  value,
) {
  if (!finite(value)) {
    return "na";
  }

  return Number(value)
    .toFixed(4);
}

export function createTradeCandidateKey({
  symbol,
  setup,
  entryPrice,
  signalTime,
}) {
  return [
    String(symbol || "")
      .trim()
      .toUpperCase(),

    String(setup || "unknown"),

    roundCandidatePrice(
      entryPrice,
    ),

    finite(signalTime)
      ? Math.floor(
          Number(signalTime),
        )
      : "na",
  ].join("|");
}

export function createTradeMemoryRecord({
  state,
  decision,
  gateResult,
}) {
  const analysis =
    decision?.analysis || {};

  const plan =
    decision?.plan || {};

  const gate =
    gateResult?.gate || {};

  const signalTime =
    analysis.latestBarTime ??
    analysis.time ??
    null;

  const candidateKey =
    createTradeCandidateKey({
      symbol:
        state?.symbol,

      setup:
        analysis.setup,

      entryPrice:
        plan.entryPrice ??
        analysis.currentPrice,

      signalTime,
    });

  return {
    id: createId(),

    version:
      TRADE_MEMORY_VERSION,

    createdAt:
      new Date()
        .toISOString(),

    candidateKey,

    symbol:
      String(
        state?.symbol || "",
      ).toUpperCase(),

    companyName:
      state?.context
        ?.company
        ?.name ||
      state?.companyName ||
      state?.symbol ||
      "",

    executionMode:
      "paper",

    cashBuyOnly:
      true,

    shortSellingEnabled:
      false,

    liveExecutionAllowed:
      false,

    status:
      "pending",

    outcome:
      "判定待ち",

    decision:
      gate.decision || null,

    confidence:
      finite(gate.confidence)
        ? Number(
            gate.confidence,
          )
        : null,

    summary:
      gate.summary || "",

    reasons:
      Array.isArray(
        gate.reasons,
      )
        ? gate.reasons
        : [],

    riskFlags:
      Array.isArray(
        gate.riskFlags,
      )
        ? gate.riskFlags
        : [],

    conditionsToApprove:
      Array.isArray(
        gate.conditionsToApprove,
      )
        ? gate.conditionsToApprove
        : [],

    disclaimer:
      gate.disclaimer || "",

    model:
      gateResult?.meta
        ?.model || null,

    responseId:
      gateResult?.meta
        ?.responseId || null,

    generatedAt:
      gateResult?.meta
        ?.generatedAt || null,

    setup:
      analysis.setup || null,

    setupLabel:
      decision?.setupLabel ||
      null,

    signalTime:
      finite(signalTime)
        ? Number(signalTime)
        : null,

    candidatePrice:
      finite(
        analysis.currentPrice,
      )
        ? Number(
            analysis.currentPrice,
          )
        : null,

    entryPrice:
      finite(plan.entryPrice)
        ? Number(
            plan.entryPrice,
          )
        : null,

    stopPrice:
      finite(plan.stopPrice)
        ? Number(
            plan.stopPrice,
          )
        : null,

    firstTargetPrice:
      finite(
        plan.firstTargetPrice,
      )
        ? Number(
            plan.firstTargetPrice,
          )
        : null,

    secondTargetPrice:
      finite(
        plan.secondTargetPrice,
      )
        ? Number(
            plan.secondTargetPrice,
          )
        : null,

    riskReward:
      finite(plan.riskReward)
        ? Number(
            plan.riskReward,
          )
        : null,

    quantity:
      finite(plan.quantity)
        ? Number(
            plan.quantity,
          )
        : null,

    intraday: {
      vwap:
        finite(analysis.vwap)
          ? Number(
              analysis.vwap,
            )
          : null,

      atr:
        finite(analysis.atr)
          ? Number(
              analysis.atr,
            )
          : null,

      volumeRatio:
        finite(
          analysis.volumeRatio,
        )
          ? Number(
              analysis.volumeRatio,
            )
          : null,

      priorHigh:
        finite(
          analysis.priorHigh,
        )
          ? Number(
              analysis.priorHigh,
            )
          : null,

      priorLow:
        finite(
          analysis.priorLow,
        )
          ? Number(
              analysis.priorLow,
            )
          : null,

      setupStrengthScore:
        finite(
          analysis
            .setupStrengthScore,
        )
          ? Number(
              analysis
                .setupStrengthScore,
            )
          : null,

      dataQualityScore:
        finite(
          analysis
            .dataQualityScore,
        )
          ? Number(
              analysis
                .dataQualityScore,
            )
          : null,

      dataAgeSeconds:
        finite(
          analysis.dataAgeSeconds,
        )
          ? Number(
              analysis.dataAgeSeconds,
            )
          : null,
    },

    daily: {
      totalScore:
        finite(
          state?.analysis
            ?.totalScore,
        )
          ? Number(
              state.analysis
                .totalScore,
            )
          : null,

      technicalScore:
        finite(
          state?.analysis
            ?.technicalScore,
        )
          ? Number(
              state.analysis
                .technicalScore,
            )
          : null,

      verdict:
        state?.analysis
          ?.verdict || null,

      predictionDirection:
        state?.prediction
          ?.direction || null,

      predictionConfidence:
        finite(
          state?.prediction
            ?.confidence,
        )
          ? Number(
              state.prediction
                .confidence,
            )
          : null,

      marketRegime:
        state
          ?.marketEnvironment
          ?.regime || null,

      indicators: {
        currentPrice:
          finite(
            state?.indicators
              ?.currentPrice,
          )
            ? Number(
                state.indicators
                  .currentPrice,
              )
            : null,

        rsi:
          finite(
            state?.indicators
              ?.rsi,
          )
            ? Number(
                state.indicators
                  .rsi,
              )
            : null,

        movingAverages:
          state?.indicators
            ?.movingAverages ||
          null,

        macd:
          state?.indicators
            ?.macd || null,

        adx:
          finite(
            state?.indicators
              ?.adx,
          )
            ? Number(
                state.indicators
                  .adx,
              )
            : state?.indicators
                ?.adx || null,
      },
    },

    evaluation: {
      evaluatedAt: null,
      exitPrice: null,
      actualReturnPercent:
        null,
      maximumFavorableMovePercent:
        null,
      maximumAdverseMovePercent:
        null,
      hit: null,
    },
  };
}

export function saveTradeMemoryRecord(
  record,
) {
  const records =
    getTradeMemory();

  const duplicate =
    records.find(
      (stored) =>
        stored.candidateKey ===
          record.candidateKey &&
        stored.decision ===
          record.decision &&
        stored.model ===
          record.model,
    );

  if (duplicate) {
    return {
      record:
        duplicate,

      saved: false,
      duplicate: true,
    };
  }

  records.push(record);

  setTradeMemory(records);

  return {
    record,
    saved: true,
    duplicate: false,
  };
}

export function summarizeTradeMemory(
  records = [],
) {
  const safeRecords =
    Array.isArray(records)
      ? records
      : [];

  const decisionCounts = {
    approve: 0,
    wait: 0,
    reject: 0,
  };

  let resolvedCount = 0;
  let winningApprovalCount = 0;
  let resolvedApprovalCount = 0;

  safeRecords.forEach(
    (record) => {
      if (
        Object.hasOwn(
          decisionCounts,
          record.decision,
        )
      ) {
        decisionCounts[
          record.decision
        ] += 1;
      }

      if (
        record.status ===
          "resolved"
      ) {
        resolvedCount += 1;

        if (
          record.decision ===
            "approve"
        ) {
          resolvedApprovalCount += 1;

          if (
            record.evaluation
              ?.hit === true
          ) {
            winningApprovalCount += 1;
          }
        }
      }
    },
  );

  return {
    totalCount:
      safeRecords.length,

    pendingCount:
      safeRecords.filter(
        (record) =>
          record.status ===
          "pending",
      ).length,

    resolvedCount,

    approveCount:
      decisionCounts.approve,

    waitCount:
      decisionCounts.wait,

    rejectCount:
      decisionCounts.reject,

    approvalWinRate:
      resolvedApprovalCount > 0
        ? (
            winningApprovalCount /
            resolvedApprovalCount
          ) * 100
        : null,
  };
}

export function clearTradeMemory() {
  if (storageAvailable()) {
    globalThis.localStorage
      .removeItem(
        STORAGE_KEYS.tradeMemory,
      );
  }

  void openTradeMemoryDatabase()
    .then((database) => {
      if (!database) {
        return;
      }

      const transaction =
        database.transaction(
          RECORD_STORE,
          "readwrite",
        );

      transaction
        .objectStore(
          RECORD_STORE,
        )
        .clear();

      transaction.oncomplete =
        () =>
          database.close();
    });
}

export const TradeMemoryInternals = {
  finite,
  indexedTradeMemory,
  openTradeMemoryDatabase,
  persistTradeMemory,
};