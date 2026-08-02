function createBrokerAuditLog({
  maximumEntries = 500,
} = {}) {
  const entries = [];

  function record({
    event,
    details = {},
  } = {}) {
    if (!event) {
      throw new Error(
        "Audit event is required.",
      );
    }

    const entry = {
      id:
        `broker-audit-${Date.now()}-${entries.length + 1}`,

      event:
        String(event),

      details:
        structuredClone(
          details,
        ),

      recordedAt:
        new Date()
          .toISOString(),

      readOnly:
        true,
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

  return {
    record,
    list,
  };
}

module.exports = {
  createBrokerAuditLog,
};