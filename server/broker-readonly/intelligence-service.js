const {
  createBrokerMetricsHistory,
} = require("./metrics-history");

const {
  createBrokerReportCache,
} = require("./report-cache");

const {
  createBrokerAuditLog,
} = require("./audit-log");

const {
  createBrokerIntelligenceReport,
} = require("./report");

function createBrokerIntelligenceService() {
  const history =
    createBrokerMetricsHistory();

  const cache =
    createBrokerReportCache();

  const audit =
    createBrokerAuditLog();

  function analyze(
    metrics = {},
  ) {
    history.add(
      metrics,
    );

    const report =
      createBrokerIntelligenceReport({
        metrics,

        history:
          history.list(),
      });

    cache.set(
      report,
    );

    audit.record({
      event:
        "broker_intelligence_analyzed",

      details: {
        score:
          report
            .intelligence
            .recommendation
            .score,

        policyAllowed:
          report
            .policy
            .allowed,
      },
    });

    return report;
  }

  function getLatestReport() {
    return cache.get();
  }

  function getHistory() {
    return history.list();
  }

  function getAuditLog() {
    return audit.list();
  }

  return {
    analyze,
    getLatestReport,
    getHistory,
    getAuditLog,
  };
}

module.exports = {
  createBrokerIntelligenceService,
};