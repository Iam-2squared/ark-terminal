const handlers = {
  connection: require("../../server/broker-readonly/connection.js"),
  account: require("../../server/broker-readonly/account.js"),
  positions: require("../../server/broker-readonly/positions.js"),
  orders: require("../../server/broker-readonly/orders.js"),
  health: require("../../server/broker-readonly/health.js"),
  availability: require("../../server/broker-readonly/availability.js"),
  diagnostics: require("../../server/broker-readonly/diagnostics.js")
};

function resolveRoute(req) {
  const path = req.query?.path;

  if (Array.isArray(path)) {
    return String(path[0] || "").toLowerCase();
  }

  return String(path || "")
    .split("/")[0]
    .toLowerCase();
}

module.exports = async function handler(req, res) {
  const route = resolveRoute(req);
  const selected = handlers[route];

  if (typeof selected !== "function") {
    res.status(404).json({
      ok: false,
      error: "broker_route_not_found",
      route
    });

    return;
  }

  return selected(req, res);
};