// Part262 B4 AI Broker Score

const { analyzeBroker } = require("./intelligence");

function calculateBrokerScore(metrics = {}) {
    const result = analyzeBroker(metrics);

    return {
        score: result.health.score,
        grade:
            result.health.score >= 90 ? "A" :
            result.health.score >= 80 ? "B" :
            result.health.score >= 70 ? "C" :
            result.health.score >= 60 ? "D" :
            "E",

        recommendation: result.recommendation,
    };
}

module.exports = {
    calculateBrokerScore,
};
