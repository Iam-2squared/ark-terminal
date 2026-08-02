// Part262 B3 Broker Intelligence Engine

const { evaluateBrokerHealth } = require("./health-model");

function analyzeBroker(metrics = {}) {
    const health = evaluateBrokerHealth(metrics);

    return {
        broker: "Ark ReadOnly",
        recommendation:
            health.score >= 90 ? "Ready" :
            health.score >= 70 ? "Monitor" :
            "Investigate",

        health,
    };
}

module.exports = {
    analyzeBroker,
};
