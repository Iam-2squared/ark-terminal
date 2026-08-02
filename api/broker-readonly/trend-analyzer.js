function average(
  values,
) {
  if (
    values.length ===
    0
  ) {
    return null;
  }

  return (
    values.reduce(
      (
        total,
        value,
      ) =>
        total + value,
      0,
    ) /
    values.length
  );
}

function finiteValues(
  entries,
  key,
) {
  return entries
    .map(
      (
        entry,
      ) =>
        Number(
          entry?.metrics?.[
            key
          ],
        ),
    )
    .filter(
      Number.isFinite,
    );
}

function analyzeBrokerTrend(
  entries = [],
) {
  if (
    !Array.isArray(entries) ||
    entries.length < 2
  ) {
    return {
      direction:
        "insufficient_data",

      improving:
        false,

      deteriorating:
        false,

      sampleCount:
        Array.isArray(entries)
          ? entries.length
          : 0,
    };
  }

  const midpoint =
    Math.floor(
      entries.length / 2,
    );

  const earlier =
    entries.slice(
      0,
      midpoint,
    );

  const recent =
    entries.slice(
      midpoint,
    );

  const earlierLatency =
    average(
      finiteValues(
        earlier,
        "latency",
      ),
    );

  const recentLatency =
    average(
      finiteValues(
        recent,
        "latency",
      ),
    );

  const earlierErrors =
    average(
      finiteValues(
        earlier,
        "errors",
      ),
    );

  const recentErrors =
    average(
      finiteValues(
        recent,
        "errors",
      ),
    );

  let improvingSignals = 0;
  let deterioratingSignals = 0;

  if (
    earlierLatency !== null &&
    recentLatency !== null
  ) {
    if (
      recentLatency <
      earlierLatency
    ) {
      improvingSignals += 1;
    }
    else if (
      recentLatency >
      earlierLatency
    ) {
      deterioratingSignals += 1;
    }
  }

  if (
    earlierErrors !== null &&
    recentErrors !== null
  ) {
    if (
      recentErrors <
      earlierErrors
    ) {
      improvingSignals += 1;
    }
    else if (
      recentErrors >
      earlierErrors
    ) {
      deterioratingSignals += 1;
    }
  }

  const direction =
    improvingSignals >
    deterioratingSignals
      ? "improving"
      : deterioratingSignals >
          improvingSignals
        ? "deteriorating"
        : "stable";

  return {
    direction,

    improving:
      direction ===
      "improving",

    deteriorating:
      direction ===
      "deteriorating",

    sampleCount:
      entries.length,

    earlierLatency,
    recentLatency,
    earlierErrors,
    recentErrors,
  };
}

module.exports = {
  analyzeBrokerTrend,
};