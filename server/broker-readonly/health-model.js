// Part262 B2 AI Health Model

function evaluateBrokerHealth(metrics = {}) {
    const latency = metrics.latency ?? 0;
    const uptime = metrics.uptime ?? 100;
    const errors = metrics.errors ?? 0;

    let score = 100;

    score -= Math.min(latency / 10, 30);
    score -= errors * 5;
    score += (uptime - 95) * 2;

    score = Math.max(0, Math.min(100, Math.round(score)));

    return {
        score,
        status:
            score >= 90 ? "Excellent" :
            score >= 75 ? "Good" :
            score >= 50 ? "Warning" :
            "Critical"
    };
}

module.exports = {
    evaluateBrokerHealth,
};
