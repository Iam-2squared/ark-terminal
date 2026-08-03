export function calculateFeatureImportance(features = {}, prediction = {}) {
    const entries = Object.entries(features)
        .filter(([, value]) => Number.isFinite(value));

    const total = entries.reduce((s, [, v]) => s + Math.abs(v), 0) || 1;

    return entries
        .map(([name, value]) => ({
            name,
            value,
            weight: Math.abs(value) / total,
            contribution:
                (prediction.score ?? 0) * (Math.abs(value) / total)
        }))
        .sort((a, b) => b.weight - a.weight);
}
