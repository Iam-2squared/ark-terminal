// Part262 B5 AI Broker Recommendation

const { calculateBrokerScore } = require("./score");

function buildRecommendation(metrics = {}) {
    const result = calculateBrokerScore(metrics);

    let action;

    if (result.score >= 90) {
        action = "READY";
    } else if (result.score >= 75) {
        action = "MONITOR";
    } else if (result.score >= 60) {
        action = "CAUTION";
    } else {
        action = "BLOCK";
    }

    return {
        action,
        score: result.score,
        grade: result.grade,
        recommendation: result.recommendation,
    };
}

module.exports = {
    buildRecommendation,
};
