const {
  createRuntime,
} = require("./runtime");

function initializeRuntime() {
  return createRuntime();
}

module.exports = {
  initializeRuntime,
};