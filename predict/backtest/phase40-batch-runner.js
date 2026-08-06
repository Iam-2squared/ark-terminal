import { runWalkForwardBacktest } from "./engine.js";

const PHASE40_BATCH_SAFETY = Object.freeze({
  mode: "HISTORICAL_BACKTEST_ONLY",
  brokerWriteAllowed: false,
  liveTradingAllowed: false,
  orderCreationAllowed: false,
  orderTransmissionAllowed: false,
  orderCancellationAllowed: false,
  orderModificationAllowed: false,
  excelOrderWriteAllowed: false,
  orderTriggerWriteAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
});

function positiveInteger(value, fallback) {
  const number = Math.trunc(Number(value));
  return Number.isFinite(number) && number > 0 ? number : fallback;
}

function normalizeTask(task, index) {
  if (!task || typeof task !== "object") throw new TypeError(`task ${index} is required`);
  const symbol = String(task.symbol ?? "").toUpperCase();
  if (!symbol) throw new TypeError(`task ${index} symbol is required`);
  if (!Array.isArray(task.candles)) throw new TypeError(`task ${symbol} candles are required`);
  return {
    taskId: String(task.taskId ?? `${symbol}:${task.period ?? 5}:${index}`),
    symbol,
    companyName: task.companyName ?? symbol,
    industry: task.industry ?? "UNKNOWN",
    period: positiveInteger(task.period, 5),
    candles: task.candles,
    weights: task.weights ?? {},
    maximumSamples: positiveInteger(task.maximumSamples, 300),
    costs: task.costs,
    historyMetadata: task.historyMetadata ?? {},
    calibration: task.calibration,
  };
}

export function createPhase40BatchPlan({ tasks = [], options = {}, checkpoint = null } = {}) {
  const normalizedTasks = tasks.map(normalizeTask);
  const completedTaskIds = new Set(checkpoint?.completedTaskIds ?? []);
  const failedTaskIds = new Set(checkpoint?.failedTaskIds ?? []);
  const retryFailed = options.retryFailed === true;
  const pending = normalizedTasks.filter((task) => {
    if (completedTaskIds.has(task.taskId)) return false;
    if (!retryFailed && failedTaskIds.has(task.taskId)) return false;
    return true;
  });
  return {
    planId: options.planId ?? `phase40-batch-${Date.now()}`,
    concurrency: positiveInteger(options.concurrency, 2),
    totalTasks: normalizedTasks.length,
    pendingTasks: pending,
    skippedCompleted: normalizedTasks.length - pending.length - [...failedTaskIds].filter((id) => normalizedTasks.some((task) => task.taskId === id) && !retryFailed).length,
    skippedFailed: retryFailed ? 0 : normalizedTasks.filter((task) => failedTaskIds.has(task.taskId)).length,
    safety: { ...PHASE40_BATCH_SAFETY },
  };
}

function summarizeResult(task, result) {
  return {
    taskId: task.taskId,
    symbol: task.symbol,
    period: task.period,
    trainingSamples: result?.partitions?.training?.length ?? result?.training?.length ?? null,
    validationSamples: result?.partitions?.validation?.length ?? result?.validation?.length ?? null,
    testSamples: result?.partitions?.test?.length ?? result?.test?.length ?? null,
    metrics: result?.metrics ?? result?.testMetrics ?? result?.summary ?? null,
    status: "COMPLETED",
  };
}

async function executeTask(task, runner) {
  try {
    const result = await runner(task);
    return { ok: true, value: summarizeResult(task, result), raw: result };
  } catch (error) {
    return {
      ok: false,
      value: {
        taskId: task.taskId,
        symbol: task.symbol,
        period: task.period,
        status: "FAILED",
        error: error instanceof Error ? error.message : String(error),
      },
    };
  }
}

export async function runPhase40BatchBacktest({ tasks = [], options = {}, checkpoint = null, runner } = {}) {
  const plan = createPhase40BatchPlan({ tasks, options, checkpoint });
  const taskRunner = runner ?? ((task) => runWalkForwardBacktest(task));
  const completed = [...(checkpoint?.completed ?? [])];
  const failed = [...(checkpoint?.failed ?? [])];
  const rawResults = [];
  let cursor = 0;

  async function worker() {
    while (true) {
      const current = cursor;
      cursor += 1;
      if (current >= plan.pendingTasks.length) return;
      const task = plan.pendingTasks[current];
      const outcome = await executeTask(task, taskRunner);
      if (outcome.ok) {
        completed.push(outcome.value);
        rawResults.push({ taskId: task.taskId, result: outcome.raw });
      } else {
        failed.push(outcome.value);
      }
    }
  }

  await Promise.all(Array.from({ length: Math.min(plan.concurrency, Math.max(1, plan.pendingTasks.length)) }, () => worker()));

  const checkpointOut = {
    planId: plan.planId,
    completedTaskIds: completed.map((item) => item.taskId),
    failedTaskIds: failed.map((item) => item.taskId),
    completed,
    failed,
    updatedAt: options.updatedAt ?? new Date().toISOString(),
    immutable: true,
    safety: { ...PHASE40_BATCH_SAFETY },
  };

  const groupedBySymbol = Object.values(completed.reduce((groups, item) => {
    const current = groups[item.symbol] ?? { symbol: item.symbol, completedRuns: 0, periods: [] };
    current.completedRuns += 1;
    current.periods.push(item.period);
    groups[item.symbol] = current;
    return groups;
  }, {}));

  return {
    status: failed.length ? "COMPLETED_WITH_FAILURES" : "COMPLETED",
    plan,
    completed,
    failed,
    groupedBySymbol,
    rawResults,
    checkpoint: checkpointOut,
    brokerWrites: 0,
    liveOrders: 0,
    safety: { ...PHASE40_BATCH_SAFETY },
  };
}

export function buildPhase40ResumeCheckpoint(result) {
  if (!result?.checkpoint) throw new TypeError("batch result checkpoint is required");
  return {
    ...result.checkpoint,
    immutable: true,
    safety: { ...PHASE40_BATCH_SAFETY },
  };
}

export { PHASE40_BATCH_SAFETY };
