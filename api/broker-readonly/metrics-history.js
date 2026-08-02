function createBrokerMetricsHistory({
  maximumEntries = 200,
} = {}) {
  const entries = [];

  function add(
    metrics = {},
  ) {
    const entry = {
      id:
        `broker-metric-${Date.now()}-${entries.length + 1}`,

      recordedAt:
        new Date()
          .toISOString(),

      metrics:
        structuredClone(
          metrics,
        ),
    };

    entries.push(
      entry,
    );

    while (
      entries.length >
      maximumEntries
    ) {
      entries.shift();
    }

    return structuredClone(
      entry,
    );
  }

  function list() {
    return structuredClone(
      entries,
    );
  }

  function latest() {
    if (
      entries.length ===
      0
    ) {
      return null;
    }

    return structuredClone(
      entries[
        entries.length - 1
      ],
    );
  }

  function clear() {
    entries.length = 0;
  }

  return {
    add,
    list,
    latest,
    clear,
  };
}

module.exports = {
  createBrokerMetricsHistory,
};