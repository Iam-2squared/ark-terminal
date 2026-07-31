import { activeConditionsForRecord } from "./feature-extractor.js";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function chronologicalPartitions(records) {
  const ordered = [...records].sort(
    (first, second) =>
      new Date(first.createdAt) - new Date(second.createdAt),
  );
  const trainingEnd = Math.floor(ordered.length * 0.6);
  const validationEnd = Math.floor(ordered.length * 0.8);

  return ordered.map((record, index) => ({
    record,
    fallbackPartition:
      index < trainingEnd
        ? "training"
        : index < validationEnd
          ? "validation"
          : "test",
  }));
}

function featureRow(record) {
  const confidence = Number(record.confidence?.score ?? record.confidence);

  return {
    predictionScore: finite(record.score) ? Number(record.score) : null,
    predictionPeriod: Number(record.period) || null,
    predictionPrice: finite(record.predictionPrice)
      ? Number(record.predictionPrice)
      : null,
    confidence: finite(confidence) ? confidence : null,
    downsideRisk: finite(record.downsideRisk)
      ? Number(record.downsideRisk)
      : null,
    marketRegime: record.marketRegime || "未取得",
    market: record.market || record.exchange || "未取得",
    industry: record.industry || "未分類",
    factorScores: {
      ...(record.factorScores || {}),
    },
    indicatorValues: {
      ...(record.features?.values || {}),
    },
    activeConditions: activeConditionsForRecord(record).map(
      (condition) => condition.key,
    ),
  };
}

function labelRow(record) {
  return {
    hit: Boolean(record.hit),
    actualReturn: Number(record.actualReturn),
    strategyReturn: finite(record.strategyReturn)
      ? Number(record.strategyReturn)
      : null,
    expectedReturn: finite(record.expectedReturn)
      ? Number(record.expectedReturn)
      : null,
    forecastError:
      finite(record.expectedReturn) && finite(record.actualReturn)
        ? Number(record.actualReturn) - Number(record.expectedReturn)
        : null,
  };
}

export function buildMachineLearningDataset(records) {
  const eligible = records.filter(
    (record) =>
      record.status === "resolved" && finite(record.actualReturn),
  );
  const rows = chronologicalPartitions(eligible).map(
    ({ record, fallbackPartition }) => ({
      id: record.id,
      symbol: record.symbol,
      featureTimestamp: record.analysisTime || record.createdAt,
      labelTimestamp: record.resolvedAt,
      split: record.partition || fallbackPartition,
      features: featureRow(record),
      label: labelRow(record),
      audit: {
        source: record.source || "legacy",
        featureSchemaVersion: record.features?.schemaVersion || 0,
        futureInformationIncluded: false,
      },
    }),
  );

  return {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    splitMethod: "chronological-60-20-20-or-existing-walk-forward-partition",
    featureDefinition:
      "予測時点で保存した指標値・条件・スコアだけを使用",
    labelDefinition: "予測期間経過後の実リターンと費用後損益",
    rows,
    partitions: {
      training: rows.filter((row) => row.split === "training"),
      validation: rows.filter((row) => row.split === "validation"),
      test: rows.filter((row) => row.split === "test"),
    },
  };
}

export function exportMachineLearningDataset(records) {
  return JSON.stringify(buildMachineLearningDataset(records), null, 2);
}
