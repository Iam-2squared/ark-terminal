function createBrokerReportCache({
  ttlMilliseconds = 30000,
  nowProvider =
    () =>
      Date.now(),
} = {}) {
  let cached = null;

  function set(
    report,
  ) {
    cached = {
      report:
        structuredClone(
          report,
        ),

      storedAt:
        nowProvider(),
    };

    return get();
  }

  function get() {
    if (!cached) {
      return null;
    }

    const age =
      nowProvider() -
      cached.storedAt;

    if (
      age >
      ttlMilliseconds
    ) {
      cached = null;
      return null;
    }

    return structuredClone(
      cached.report,
    );
  }

  function clear() {
    cached = null;
  }

  return {
    set,
    get,
    clear,
  };
}

module.exports = {
  createBrokerReportCache,
};