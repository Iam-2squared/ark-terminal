function createAdvisorAudit() {
  const entries = [];

  function record(result = {}) {
    const entry = {
      id:
        `advisor-${Date.now()}-${entries.length + 1}`,

      createdAt:
        new Date().toISOString(),

      symbol:
        result.symbol || "",

      recommendation:
        result.recommendation?.recommendation ||
        "UNKNOWN",

      safetyAllowed:
        result.safety?.allowed === true,

      score:
        result.score?.score ?? null,
    };

    entries.push(entry);

    return structuredClone(entry);
  }

  function list() {
    return structuredClone(entries);
  }

  function latest() {
    return entries.length
      ? structuredClone(
          entries[entries.length - 1]
        )
      : null;
  }

  return {
    record,
    list,
    latest,
  };
}

module.exports = {
  createAdvisorAudit,
};