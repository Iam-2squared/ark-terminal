function createPortfolioHistory({
  maximumEntries = 200,
} = {}) {
  const entries = [];

  function add(
    snapshot = {},
  ) {
    const entry = {
      id:
        `portfolio-${Date.now()}-${entries.length + 1}`,

      recordedAt:
        new Date()
          .toISOString(),

      snapshot:
        structuredClone(
          snapshot,
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
  createPortfolioHistory,
};