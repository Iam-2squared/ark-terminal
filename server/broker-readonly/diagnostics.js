const {
  evaluateBrokerGuard,
} = require("./guard");

const {
  evaluateBrokerRisk,
} = require("./risk");

function diagnoseBroker(
  metrics = {},
) {
  const guard =
    evaluateBrokerGuard(
      metrics,
    );

  const risk =
    evaluateBrokerRisk(
      metrics,
    );

  const issues = [
    ...guard.reasons,
    ...risk.factors,
  ];

  return {
    healthy:
      guard.passed &&
      risk.level ===
        "low",

    severity:
      !guard.passed ||
      risk.level ===
        "critical"
        ? "critical"
        : risk.level ===
            "high"
          ? "warning"
          : issues.length > 0
            ? "notice"
            : "normal",

    issues:
      [
        ...new Set(
          issues,
        ),
      ],

    guard,
    risk,

    readOnly:
      true,
  };
}

module.exports = {
  diagnoseBroker,
};