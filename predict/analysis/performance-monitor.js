function number(value, fallback = 0) {
  const parsed = Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : fallback;
}

function round(value, digits = 2) {
  const factor = 10 ** digits;

  return (
    Math.round(
      number(value) * factor,
    ) / factor
  );
}

function now() {
  return (
    globalThis.performance?.now?.() ??
    Date.now()
  );
}

/*
 * Prediction accuracy API
 * Kept for Prediction Lab compatibility.
 */
export function evaluatePredictionHistory({
  history = [],
} = {}) {
  const safeHistory =
    Array.isArray(history)
      ? history
      : [];

  const total =
    safeHistory.length;

  if (total === 0) {
    return {
      total: 0,
      accuracy: 0,
      averageReturn: 0,
      winRate: 0,
    };
  }

  const wins =
    safeHistory.filter(
      (item) =>
        number(item?.return) > 0,
    ).length;

  const averageReturn =
    safeHistory.reduce(
      (sum, item) =>
        sum +
        number(item?.return),
      0,
    ) / total;

  const winRate =
    round(
      (
        wins /
        total
      ) * 100,
      2,
    );

  return {
    total,

    accuracy:
      winRate,

    averageReturn:
      round(
        averageReturn,
        2,
      ),

    winRate,
  };
}

export function buildPerformanceGrade({
  report = {},
} = {}) {
  const accuracy =
    number(
      report.accuracy,
    );

  if (accuracy >= 90) {
    return "A";
  }

  if (accuracy >= 80) {
    return "B";
  }

  if (accuracy >= 70) {
    return "C";
  }

  if (accuracy >= 60) {
    return "D";
  }

  return "E";
}

export function buildPerformanceMonitor({
  history = [],
} = {}) {
  const report =
    evaluatePredictionHistory({
      history,
    });

  return {
    version:
      "performance-monitor-v1",

    report,

    grade:
      buildPerformanceGrade({
        report,
      }),
  };
}

/*
 * Runtime duration API
 * Added in Part79 without removing the older exports.
 */
export class PerformanceMonitor {
  constructor() {
    this.records = [];
  }

  start(name) {
    return {
      name,
      start:
        now(),
    };
  }

  end(timer = {}) {
    const duration =
      Math.max(
        0,
        now() -
        number(
          timer.start,
          now(),
        ),
      );

    const record = {
      name:
        timer.name,

      duration,

      timestamp:
        Date.now(),
    };

    this.records.push(
      record,
    );

    return record;
  }

  summary() {
    if (
      this.records.length === 0
    ) {
      return {
        count: 0,
        average: 0,
        max: 0,
        min: 0,
      };
    }

    const values =
      this.records.map(
        (record) =>
          number(
            record.duration,
          ),
      );

    return {
      count:
        values.length,

      average:
        values.reduce(
          (sum, value) =>
            sum + value,
          0,
        ) / values.length,

      max:
        Math.max(
          ...values,
        ),

      min:
        Math.min(
          ...values,
        ),
    };
  }

  clear() {
    this.records = [];
  }
}

export const performanceMonitor =
  new PerformanceMonitor();