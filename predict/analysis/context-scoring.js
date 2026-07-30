const positiveTerms = [
  "beat",
  "beats",
  "growth",
  "upgrade",
  "record",
  "profit",
  "surge",
  "strong",
  "上方修正",
  "増益",
  "最高益",
  "受注",
  "提携",
  "承認",
];

const negativeTerms = [
  "miss",
  "downgrade",
  "loss",
  "lawsuit",
  "decline",
  "weak",
  "cut",
  "下方修正",
  "減益",
  "赤字",
  "訴訟",
  "不正",
  "中止",
];

function clamp(value) {
  return Math.min(100, Math.max(0, Number(value)));
}

function verdict(score) {
  if (score >= 75) return "強気";
  if (score >= 60) return "やや強気";
  if (score >= 45) return "中立";
  if (score >= 30) return "やや弱気";
  return "弱気";
}

function createFactor({ key, label, weight, score, reason, available = true }) {
  const normalizedScore = available ? Math.round(clamp(score)) : null;

  return {
    key,
    label,
    category: "context",
    weight: Number(weight) || 0,
    score: normalizedScore,
    contribution: available
      ? (normalizedScore * (Number(weight) || 0)) / 100
      : 0,
    verdict: available ? verdict(normalizedScore) : "データなし",
    reason,
    available,
  };
}

function unavailable(key, label, weight, reason) {
  return createFactor({
    key,
    label,
    weight,
    score: 0,
    reason,
    available: false,
  });
}

export function analyzeTextSentiment(items) {
  const texts = items
    .map((item) =>
      String(item.headline || item.title || item.summary || "").toLowerCase(),
    )
    .filter(Boolean);

  if (!texts.length) return null;

  let positive = 0;
  let negative = 0;

  texts.forEach((text) => {
    positive += positiveTerms.filter((term) => text.includes(term)).length;
    negative += negativeTerms.filter((term) => text.includes(term)).length;
  });

  const total = positive + negative;

  return {
    score: total === 0 ? 50 : clamp(50 + ((positive - negative) / total) * 35),
    positive,
    negative,
    count: texts.length,
  };
}

export function scoreContextFactors(context, weights) {
  const news = analyzeTextSentiment(context?.news || []);
  const disclosures = analyzeTextSentiment(context?.disclosures || []);
  const sentiment = context?.sentiment;

  return [
    news
      ? createFactor({
          key: "news",
          label: "ニュース",
          weight: weights.news,
          score: news.score,
          reason:
            `${news.count}件の見出しを確認し、` +
            `ポジティブ語${news.positive}件、` +
            `ネガティブ語${news.negative}件を検出しました。`,
        })
      : unavailable(
          "news",
          "ニュース",
          weights.news,
          "ニュースデータが未接続、または対象記事がありません。",
        ),
    disclosures
      ? createFactor({
          key: "disclosure",
          label: "適時開示",
          weight: weights.disclosure,
          score: disclosures.score,
          reason: `${disclosures.count}件の適時開示タイトルをルールベースで評価しました。`,
        })
      : unavailable(
          "disclosure",
          "適時開示",
          weights.disclosure,
          "適時開示データソースは未接続です。",
        ),
    sentiment && Number.isFinite(Number(sentiment.score))
      ? createFactor({
          key: "sentiment",
          label: "投資家心理",
          weight: weights.sentiment,
          score: sentiment.score,
          reason:
            sentiment.reason || "接続済みの投資家心理データを評価しました。",
        })
      : unavailable(
          "sentiment",
          "投資家心理",
          weights.sentiment,
          "掲示板・SNS等の投資家心理データは未接続です。",
        ),
  ];
}
