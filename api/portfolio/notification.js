// Part263 B26 Portfolio Notification Model

function createNotification(message) {
  return {
    message,
    createdAt: new Date().toISOString(),
  };
}

module.exports = {
    createNotification,
};
