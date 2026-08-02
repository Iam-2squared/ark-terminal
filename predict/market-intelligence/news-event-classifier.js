import {
  NEWS_SOURCE_TYPES,
  clampNewsValue,
  isUsableNewsItem,
} from "./news-data-model.js";

export const NEWS_EVENT_CATEGORIES = Object.freeze({
  EARNINGS: "EARNINGS",
  GUIDANCE: "GUIDANCE",
  DIVIDEND: "DIVIDEND",
  BUYBACK: "BUYBACK",
  MERGER_ACQUISITION: "MERGER_ACQUISITION",
  FINANCING: "FINANCING",
  GOVERNANCE: "GOVERNANCE",
  REGULATORY: "REGULATORY",
  PRODUCT: "PRODUCT",
  PARTNERSHIP: "PARTNERSHIP",
  MACRO: "MACRO",
  OTHER: "OTHER",
});

const EVENT_LABELS = Object.freeze({
  EARNINGS: "決算",
  GUIDANCE: "業績予想",
  DIVIDEND: "配当",
  BUYBACK: "自己株式取得",
  MERGER_ACQUISITION: "M&A",
  FINANCING: "資金調達",
  GOVERNANCE: "経営・ガバナンス",
  REGULATORY: "規制・法務",
  PRODUCT: "製品・サービス",
  PARTNERSHIP: "提携",
  MACRO: "マクロ経済",
  OTHER: "その他",
});

const EVENT_RULES = Object.freeze([
  {
    category: NEWS_EVENT_CATEGORIES.GUIDANCE,
    terms: [
      "guidance",
      "forecast",
      "outlook",
      "profit warning",
      "業績予想",
      "上方修正",
      "下方修正",
      "見通し",
    ],
  },
  {
    category: NEWS_EVENT_CATEGORIES.EARNINGS,
    terms: [
      "earnings",
      "quarterly results",
      "financial results",
      "決算",
      "四半期報告",
      "増収",
      "増益",
      "減益",
    ],
  },
  {
    category: NEWS_EVENT_CATEGORIES.DIVIDEND,
    terms: ["dividend", "distribution", "配当", "増配", "減配", "復配"],
  },
  {
    category: NEWS_EVENT_CATEGORIES.BUYBACK,
    terms: [
      "share buyback",
      "stock repurchase",
      "自己株式取得",
      "自社株買い",
    ],
  },
  {
    category: NEWS_EVENT_CATEGORIES.MERGER_ACQUISITION,
    terms: [
      "merger",
      "acquisition",
      "takeover",
      "tender offer",
      "m&a",
      "買収",
      "合併",
      "tob",
    ],
  },
  {
    category: NEWS_EVENT_CATEGORIES.FINANCING,
    terms: [
      "public offering",
      "capital increase",
      "bond issuance",
      "資金調達",
      "増資",
      "新株発行",
      "社債発行",
    ],
  },
  {
    category: NEWS_EVENT_CATEGORIES.GOVERNANCE,
    terms: [
      "chief executive",
      "ceo",
      "director",
      "governance",
      "社長交代",
      "代表取締役",
      "取締役",
      "ガバナンス",
    ],
  },
  {
    category: NEWS_EVENT_CATEGORIES.REGULATORY,
    terms: [
      "regulator",
      "regulatory",
      "lawsuit",
      "antitrust",
      "規制",
      "訴訟",
      "行政処分",
      "課徴金",
    ],
  },
  {
    category: NEWS_EVENT_CATEGORIES.PRODUCT,
    terms: [
      "product launch",
      "new product",
      "approval",
      "新製品",
      "新サービス",
      "発売",
      "承認",
    ],
  },
  {
    category: NEWS_EVENT_CATEGORIES.PARTNERSHIP,
    terms: [
      "partnership",
      "alliance",
      "joint venture",
      "提携",
      "協業",
      "合弁",
    ],
  },
  {
    category: NEWS_EVENT_CATEGORIES.MACRO,
    terms: [
      "interest rate",
      "inflation",
      "central bank",
      "gdp",
      "金利",
      "物価",
      "中央銀行",
      "国内総生産",
    ],
  },
]);

function itemText(item) {
  return [item?.title, item?.summary, item?.body]
    .map((value) => String(value || "").toLowerCase())
    .filter(Boolean)
    .join(" ");
}

function matchesFor(text, terms) {
  return terms.filter((term) => text.includes(term.toLowerCase()));
}

function directCategory(item) {
  return item?.type === NEWS_SOURCE_TYPES.EARNINGS
    ? NEWS_EVENT_CATEGORIES.EARNINGS
    : null;
}

export function classifyNewsEvent(item = {}) {
  const text = itemText(item);

  if (!isUsableNewsItem(item) || !text) {
    return {
      category: NEWS_EVENT_CATEGORIES.OTHER,
      label: EVENT_LABELS.OTHER,
      confidence: 0,
      matchedSignals: [],
      secondaryCategories: [],
      available: false,
    };
  }

  const direct = directCategory(item);
  const matches = EVENT_RULES.map((rule) => ({
    category: rule.category,
    signals: matchesFor(text, rule.terms),
  })).filter((result) => result.signals.length > 0);
  const selected =
    (direct && matches.find((result) => result.category === direct)) ||
    (direct ? { category: direct, signals: [] } : matches[0]) ||
    { category: NEWS_EVENT_CATEGORIES.OTHER, signals: [] };
  const allCategories = [
    selected.category,
    ...matches.map((result) => result.category),
  ];
  const signalCount = matches.reduce(
    (total, result) => total + result.signals.length,
    0,
  );
  const evidenceFactor =
    selected.category === NEWS_EVENT_CATEGORIES.OTHER
      ? 0.25
      : Math.min(1, 0.6 + signalCount * 0.1 + (direct ? 0.15 : 0));

  return {
    category: selected.category,
    label: EVENT_LABELS[selected.category],
    confidence: Math.round(
      clampNewsValue(item.confidence * evidenceFactor),
    ),
    matchedSignals: [...new Set(matches.flatMap((result) => result.signals))],
    secondaryCategories: [
      ...new Set(allCategories.filter((category) => category !== selected.category)),
    ],
    available: selected.category !== NEWS_EVENT_CATEGORIES.OTHER,
  };
}

export class NewsEventClassifier {
  classify(item = {}) {
    return classifyNewsEvent(item);
  }
}

export const newsEventClassifier = new NewsEventClassifier();

export default classifyNewsEvent;
