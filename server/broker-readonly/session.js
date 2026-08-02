// Part261 B8 Broker Session Manager

function createSession() {
  return {
    id: Date.now().toString(),
    createdAt: new Date().toISOString(),
    active: true,
    readOnly: true,
  };
}

module.exports = {
  createSession,
};
