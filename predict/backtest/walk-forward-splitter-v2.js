export const WALK_FORWARD_SPLITTER_V2_VERSION =
  "walk-forward-splitter-v2";

function finiteInteger(
  value,
  fallback,
  minimum = 1,
) {
  const number =
    Number(value);

  if (!Number.isFinite(number)) {
    return fallback;
  }

  return Math.max(
    minimum,
    Math.floor(number),
  );
}

function timestampOf(record) {
  const raw =
    record?.timestamp ??
    record?.date ??
    record?.datetime ??
    record?.time;

  const timestamp =
    new Date(raw).getTime();

  return Number.isFinite(timestamp)
    ? timestamp
    : null;
}

function normalizeRecords(records = []) {
  if (!Array.isArray(records)) {
    throw new TypeError(
      "Walk-forward records must be an array.",
    );
  }

  return records
    .map(
      (
        record,
        originalIndex,
      ) => ({
        record,
        originalIndex,
        timestamp:
          timestampOf(record),
      }),
    )
    .filter(
      (
        item,
      ) =>
        item.timestamp !== null,
    )
    .sort(
      (
        left,
        right,
      ) =>
        left.timestamp -
        right.timestamp ||
        left.originalIndex -
        right.originalIndex,
    );
}

function periodMetadata(items) {
  if (!items.length) {
    return {
      start:
        null,

      end:
        null,

      size:
        0,
    };
  }

  return {
    start:
      new Date(
        items[0].timestamp,
      ).toISOString(),

    end:
      new Date(
        items[
          items.length - 1
        ].timestamp,
      ).toISOString(),

    size:
      items.length,
  };
}

function unwrap(items) {
  return items.map(
    (
      item,
    ) =>
      item.record,
  );
}

export function createWalkForwardWindows(
  records = [],
  {
    trainingSize = 120,
    validationSize = 20,
    testSize = 20,
    stepSize = 20,
    expanding = true,
    minimumWindows = 1,
  } = {},
) {
  const normalized =
    normalizeRecords(records);

  const train =
    finiteInteger(
      trainingSize,
      120,
    );

  const validation =
    finiteInteger(
      validationSize,
      20,
    );

  const test =
    finiteInteger(
      testSize,
      20,
    );

  const step =
    finiteInteger(
      stepSize,
      test,
    );

  const required =
    train +
    validation +
    test;

  const windows = [];

  for (
    let offset = 0;
    offset + required <=
      normalized.length;
    offset += step
  ) {
    const trainingStart =
      expanding
        ? 0
        : offset;

    const trainingEnd =
      offset + train;

    const validationEnd =
      trainingEnd +
      validation;

    const testEnd =
      validationEnd +
      test;

    const trainingItems =
      normalized.slice(
        trainingStart,
        trainingEnd,
      );

    const validationItems =
      normalized.slice(
        trainingEnd,
        validationEnd,
      );

    const testItems =
      normalized.slice(
        validationEnd,
        testEnd,
      );

    windows.push({
      id:
        `wf-${String(
          windows.length + 1,
        ).padStart(3, "0")}`,

      index:
        windows.length,

      expanding:
        Boolean(expanding),

      training:
        unwrap(trainingItems),

      validation:
        unwrap(validationItems),

      test:
        unwrap(testItems),

      periods: {
        training:
          periodMetadata(
            trainingItems,
          ),

        validation:
          periodMetadata(
            validationItems,
          ),

        test:
          periodMetadata(
            testItems,
          ),
      },
    });
  }

  const requiredMinimum =
    finiteInteger(
      minimumWindows,
      1,
    );

  return {
    version:
      WALK_FORWARD_SPLITTER_V2_VERSION,

    config: {
      trainingSize:
        train,

      validationSize:
        validation,

      testSize:
        test,

      stepSize:
        step,

      expanding:
        Boolean(expanding),
    },

    inputSize:
      records.length,

    validRecordCount:
      normalized.length,

    invalidRecordCount:
      records.length -
      normalized.length,

    windowCount:
      windows.length,

    ready:
      windows.length >=
      requiredMinimum,

    windows,
  };
}

export function validateWalkForwardWindows(
  report,
) {
  const errors = [];

  if (
    !report ||
    !Array.isArray(
      report.windows,
    )
  ) {
    return {
      valid:
        false,

      errors: [
        "Walk-forward report is invalid.",
      ],
    };
  }

  for (
    const window
    of report.windows
  ) {
    const trainEnd =
      new Date(
        window.periods.training.end,
      ).getTime();

    const validationStart =
      new Date(
        window.periods.validation.start,
      ).getTime();

    const validationEnd =
      new Date(
        window.periods.validation.end,
      ).getTime();

    const testStart =
      new Date(
        window.periods.test.start,
      ).getTime();

    if (
      !Number.isFinite(trainEnd) ||
      !Number.isFinite(validationStart) ||
      !Number.isFinite(validationEnd) ||
      !Number.isFinite(testStart)
    ) {
      errors.push(
        `${window.id}: period metadata is invalid.`,
      );

      continue;
    }

    if (trainEnd >= validationStart) {
      errors.push(
        `${window.id}: training overlaps validation.`,
      );
    }

    if (validationEnd >= testStart) {
      errors.push(
        `${window.id}: validation overlaps test.`,
      );
    }
  }

  return {
    valid:
      errors.length === 0,

    errors,
  };
}

export class WalkForwardSplitterV2 {
  constructor(config = {}) {
    this.config = {
      ...config,
    };
  }

  split(records = []) {
    return createWalkForwardWindows(
      records,
      this.config,
    );
  }
}

export default createWalkForwardWindows;