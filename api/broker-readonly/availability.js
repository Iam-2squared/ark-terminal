function calculateAvailability({
  successfulChecks = 0,
  totalChecks = 0,
} = {}) {
  const success =
    Math.max(
      0,
      Number(
        successfulChecks,
      ) || 0,
    );

  const total =
    Math.max(
      0,
      Number(
        totalChecks,
      ) || 0,
    );

  const percent =
    total > 0
      ? (
          success /
          total
        ) * 100
      : null;

  return {
    successfulChecks:
      success,

    totalChecks:
      total,

    availabilityPercent:
      percent,

    status:
      percent === null
        ? "unknown"
        : percent >= 99.9
          ? "excellent"
          : percent >= 99
            ? "good"
            : percent >= 95
              ? "warning"
              : "critical",
  };
}

module.exports = {
  calculateAvailability,
};