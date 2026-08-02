// Part261 B9 Read-only Broker API

const { initializeRuntime } = require("./integration");
const { createSession } = require("./session");

function initializeBrokerApi() {
  return {
    runtime: initializeRuntime(),
    session: createSession(),
  };
}

module.exports = {
  initializeBrokerApi,
};
