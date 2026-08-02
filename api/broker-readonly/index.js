module.exports = async function handler(req, res) {
  res.status(200).json({
    ok: true,
    service: "broker-readonly",
    mode: "read-only",
    routes: [
      "connection",
      "account",
      "positions",
      "orders",
      "health",
      "availability",
      "diagnostics"
    ],
    liveTradingAllowed: false,
    orderSubmissionAllowed: false
  });
};