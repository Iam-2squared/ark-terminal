function createIntegrationHistory({
  maximumEntries = 200,
} = {}) {
  const entries = [];

  function add(result = {}) {
    const entry = {
      id:
        `integration-${Date.now()}-${entries.length + 1}`,

      recordedAt:
        new Date().toISOString(),

      result:
        structuredClone(result),
    };

    entries.push(entry);

    while (
      entries.length >
      maximumEntries
    ) {
      entries.shift();
    }

    return structuredClone(entry);
  }

  function list() {
    return structuredClone(entries);
  }

  function latest() {
    return entries.length
      ? structuredClone(
          entries[
            entries.length - 1
          ],
        )
      : null;
  }

  return {
    add,
    list,
    latest,
  };
}

module.exports = {
  createIntegrationHistory,
};