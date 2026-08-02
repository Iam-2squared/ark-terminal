const {
  runAdvisor,
} = require("./engine");

const {
  createAdvisorAudit,
} = require("./audit");

function createAdvisorService() {
  const audit =
    createAdvisorAudit();

  function analyze(input = {}) {
    const result =
      runAdvisor(input);

    audit.record(result);

    return result;
  }

  function getAudit() {
    return audit.list();
  }

  function getLatestAudit() {
    return audit.latest();
  }

  return {
    analyze,
    getAudit,
    getLatestAudit,
  };
}

module.exports = {
  createAdvisorService,
};