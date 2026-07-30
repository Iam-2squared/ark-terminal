export const extensionRegistry = Object.freeze([
  {
    id: "earnings",
    label: "決算分析",
    category: "fundamental",
    status: "planned",
  },
  {
    id: "tdnet",
    label: "適時開示AI分析",
    category: "disclosure",
    status: "adapter-ready",
  },
  {
    id: "yahoo-board",
    label: "Yahoo掲示板分析",
    category: "sentiment",
    status: "planned",
  },
  {
    id: "x",
    label: "X分析",
    category: "sentiment",
    status: "planned",
  },
  {
    id: "reddit",
    label: "Reddit分析",
    category: "sentiment",
    status: "planned",
  },
  {
    id: "fear-greed",
    label: "Fear & Greed Index",
    category: "macro",
    status: "planned",
  },
  {
    id: "options",
    label: "オプション市場",
    category: "derivatives",
    status: "planned",
  },
  {
    id: "institutional-flow",
    label: "機関投資家売買",
    category: "flow",
    status: "planned",
  },
  {
    id: "short-interest",
    label: "空売り比率",
    category: "flow",
    status: "planned",
  },
  {
    id: "margin-ratio",
    label: "信用倍率",
    category: "flow",
    status: "planned",
  },
  {
    id: "volume-anomaly",
    label: "出来高急増検知",
    category: "anomaly",
    status: "technical-ready",
  },
  {
    id: "anomaly-detection",
    label: "異常値検知",
    category: "anomaly",
    status: "planned",
  },
  {
    id: "generative-comment",
    label: "生成AI総合コメント",
    category: "explanation",
    status: "adapter-ready",
  },
  {
    id: "broker-api",
    label: "自動売買API",
    category: "execution",
    status: "disabled",
  },
]);

export function createExtensionResult({
  id,
  available = false,
  score = null,
  reason = "",
  data = null,
}) {
  return {
    id,
    available,
    score: Number.isFinite(Number(score)) ? Number(score) : null,
    reason,
    data,
  };
}
