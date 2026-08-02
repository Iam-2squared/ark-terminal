import {
  clampNewsValue,
  isUsableNewsItem,
} from "./news-data-model.js";

export const NEWS_RISK_CATEGORIES = Object.freeze({
  FINANCIAL_DISTRESS: "FINANCIAL_DISTRESS",
  FRAUD_COMPLIANCE: "FRAUD_COMPLIANCE",
  LEGAL_REGULATORY: "LEGAL_REGULATORY",
  CYBER_OPERATIONAL: "CYBER_OPERATIONAL",
  DILUTION_FINANCING: "DILUTION_FINANCING",
  GUIDANCE_DOWNGRADE: "GUIDANCE_DOWNGRADE",
});

const RISK_RULES = Object.freeze([
  {
    category: NEWS_RISK_CATEGORIES.FINANCIAL_DISTRESS,
    severity: 90,
    terms: [
      "bankruptcy",
      "insolvency",
      "default",
      "going concern",
      "破産",
      "民事再生",
      "債務超過",
      "継続企業の前提",
    ],
  },
  {
    category: NEWS_RISK_CATEGORIES.FRAUD_COMPLIANCE,
    severity: 80,
    terms: [
      "fraud",
      "accounting irregularity",
      "misconduct",
      "不正",
      "粉飾",
      "不適切会計",
      "第三者委員会",
    ],
  },
  {
    category: NEWS_RISK_CATEGORIES.LEGAL_REGULATORY,
    severity: 65,
    terms: [
      "lawsuit",
      "regulatory investigation",
      "sanction",
      "penalty",
      "訴訟",
      "行政処分",
      "課徴金",
      "業務停止",
    ],
  },
  {
    category: NEWS_RISK_CATEGORIES.CYBER_OPERATIONAL,
    severity: 60,
    terms: [
      "cyberattack",
      "data breach",
      "recall",
      "production halt",
      "サイバー攻撃",
      "情報漏えい",
      "リコール",
      "生産停止",
    ],
  },
  {
    category: NEWS_RISK_CATEGORIES.DILUTION_FINANCING,
    severity: 45,
    terms: [
      "dilution",
      "public offering",
      "third-party allotment",
      "希薄化",
      "公募増資",
      "第三者割当増資",
    ],
  },
  {
    category: NEWS_RISK_CATEGORIES.GUIDANCE_DOWNGRADE,
    severity: 55,
    terms: [
      "profit warning",
      "guidance cut",
      "forecast lowered",
      "下方修正",
      "業績予想を引き下げ",
      "赤字転落",
    ],
  },
]);

const MITIGATION_TERMS = Object.freeze([
  "resolved",
  "settled",
  "restored",
  "limited impact",
  "解決",
  "和解",
  "復旧",
  "影響は軽微",
]);

function riskLabel(score) {
  if (score === null) return "UNKNOWN";
  if (score >= 75) return "HIGH";
  if (score >= 45) return "MEDIUM";
  if (score > 0) return "LOW";
  return "NONE";
}

function itemText(item) {
  return [item?.title, item?.summary, item?.body]
    .map((value) => String(value || "").toLowerCase())
    .filter(Boolean)
    .join(" ");
}

export function detectNewsRisk(item = {}) {
  const text = itemText(item);

  if (!isUsableNewsItem(item) || !text) {
    return {
      score: null,
      confidence: 0,
      coverage: 0,
      severity: "UNKNOWN",
      findings: [],
      mitigated: false,
    };
  }

  const findings = RISK_RULES.map((rule) => ({
    category: rule.category,
    severity: rule.severity,
    matchedSignals: rule.terms.filter((term) => text.includes(term)),
  })).filter((finding) => finding.matchedSignals.length > 0);
  const mitigated = MITIGATION_TERMS.some((term) => text.includes(term));
  const combinedProbability = findings.reduce(
    (remaining, finding) => remaining * (1 - finding.severity / 100),
    1,
  );
  const rawScore = findings.length ? (1 - combinedProbability) * 100 : 0;
  const score = clampNewsValue(rawScore * (mitigated ? 0.7 : 1));
  const evidenceFactor = findings.length
    ? Math.min(1, 0.6 + findings.length * 0.1)
    : 0.5;

  return {
    score: Math.round(score * 100) / 100,
    confidence: Math.round(
      clampNewsValue(item.confidence * evidenceFactor),
    ),
    coverage: 100,
    severity: riskLabel(score),
    findings,
    mitigated,
  };
}

export class NewsRiskEngine {
  detect(item = {}) {
    return detectNewsRisk(item);
  }
}

export const newsRiskEngine = new NewsRiskEngine();

export default detectNewsRisk;
