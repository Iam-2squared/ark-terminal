import { formatPrice } from "../symbols.js";

const elements = {};

export function initializeRenderers() {
  [
    "runPredictionButton",
    "resultCompanyName",
    "predictionBadge",
    "totalScore",
    "overallScoreLabel",
    "predictionPeriodLabel",
    "dataCompleteness",
    "technicalScore",
    "indicatorScoreList",
    "dataSourceBadge",
    "dataSourceDescription",
    "indicatorSnapshot",
    "reasonList",
    "companySnapshot",
    "newsList",
    "disclosureList",
    "sentimentSummary",
    "analysisError",
    "runBacktestButton",
    "backtestStatus",
  ].forEach((id) => {
    elements[id] = document.getElementById(id);
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function safeUrl(value) {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.toString() : "";
  } catch {
    return "";
  }
}

export function finite(value) {
  return Number.isFinite(Number(value));
}

export function formatNumber(value, digits = 2) {
  return finite(value)
    ? Number(value).toLocaleString("ja-JP", {
        maximumFractionDigits: digits,
        minimumFractionDigits: digits,
      })
    : "--";
}

function formatPercent(value) {
  return finite(value) ? `${formatNumber(value, 2)}%` : "--";
}

function formatCompact(value) {
  return finite(value)
    ? new Intl.NumberFormat("ja-JP", {
        notation: "compact",
        maximumFractionDigits: 2,
      }).format(value)
    : "--";
}

export function setAnalysisLoading(isLoading) {
  elements.runPredictionButton.disabled = isLoading;
  elements.runPredictionButton.textContent = isLoading
    ? "分析中..."
    : "分析を実行";
}

export function clearAnalysisError() {
  elements.analysisError.hidden = true;
  elements.analysisError.textContent = "";
}

export function showAnalysisError(message) {
  elements.analysisError.hidden = false;
  elements.analysisError.textContent = message;
}

export function setDataSourceStatus(text) {
  elements.dataSourceBadge.textContent = text;
}

function renderFactors(factors) {
  elements.indicatorScoreList.innerHTML = factors
    .map(
      (item) => `
        <div class="factorItem ${item.available ? "" : "unavailable"}">
          <div class="factorHeading">
            <span>${escapeHtml(item.label)}</span>
            <strong>${item.available ? `${item.score} / 100` : "--"}</strong>
          </div>
          <div class="factorMeta">
            <span class="factorVerdict">${escapeHtml(item.verdict)}</span>
            <span>重み ${formatNumber(item.weight, 1)}</span>
          </div>
          <p class="factorReason">${escapeHtml(item.reason)}</p>
          <div class="scoreBar">
            <div class="scoreBarFill" style="width: ${
              item.available ? item.score : 0
            }%"></div>
          </div>
        </div>
      `,
    )
    .join("");
}

function renderReasons(factors) {
  const ordered = [...factors].sort((first, second) => {
    if (first.available !== second.available) {
      return first.available ? -1 : 1;
    }
    return second.weight - first.weight;
  });

  elements.reasonList.innerHTML = ordered
    .map(
      (item) => `
        <div class="reasonItem">
          <strong>${escapeHtml(item.label)}</strong>
          <span>${escapeHtml(item.reason)}</span>
        </div>
      `,
    )
    .join("");
}

function renderIndicatorSnapshot(indicators, symbol) {
  const averages = indicators.movingAverages;
  const bands = indicators.bollingerBands;
  const items = [
    ["現在価格", formatPrice(indicators.currentPrice, symbol)],
    ["5MA", formatNumber(averages.ma5)],
    ["25MA", formatNumber(averages.ma25)],
    ["75MA", formatNumber(averages.ma75)],
    ["200MA", formatNumber(averages.ma200)],
    ["25日線乖離率", formatPercent(indicators.ma25Deviation)],
    ["RSI", formatNumber(indicators.rsi, 1)],
    [
      "MACD / Signal",
      indicators.macd
        ? `${formatNumber(indicators.macd.value)} / ${formatNumber(
            indicators.macd.signal,
          )}`
        : "--",
    ],
    ["ボリンジャー上限", bands ? formatNumber(bands.upper) : "--"],
    ["ボリンジャー下限", bands ? formatNumber(bands.lower) : "--"],
    [
      "出来高 / 20日平均",
      indicators.volume
        ? `${formatCompact(indicators.volume.current)} / ${formatCompact(
            indicators.volume.average,
          )}`
        : "--",
    ],
    ["ADX", indicators.adx ? formatNumber(indicators.adx.value, 1) : "--"],
    [
      "ATR",
      indicators.atr
        ? `${formatNumber(indicators.atr.value)} (${formatPercent(
            indicators.atr.percent,
          )})`
        : "--",
    ],
    [
      "ストキャスティクス",
      indicators.stochastic
        ? `%K ${formatNumber(indicators.stochastic.k, 1)} / %D ${formatNumber(
            indicators.stochastic.d,
            1,
          )}`
        : "--",
    ],
    ["VWAP（20日）", formatNumber(indicators.vwap)],
    ["52週高値との差", formatPercent(indicators.distanceFrom52WeekHigh)],
    ["52週安値との差", formatPercent(indicators.distanceFrom52WeekLow)],
  ];

  elements.indicatorSnapshot.innerHTML = items
    .map(
      ([label, value]) => `
        <div class="indicatorValue">
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(value)}</strong>
        </div>
      `,
    )
    .join("");
}

function renderCompany(company) {
  if (!company) {
    elements.companySnapshot.innerHTML =
      '<p class="emptyState">企業情報は未取得です。追加データソースを後から接続できます。</p>';
    return;
  }

  const website = safeUrl(company.website);
  const logo = safeUrl(company.logo);
  elements.companySnapshot.innerHTML = `
    <div class="companyNameRow">
      ${
        logo ? `<img src="${escapeHtml(logo)}" alt="" class="companyLogo">` : ""
      }
      <div>
        <strong>${escapeHtml(company.name)}</strong>
        <span>${escapeHtml(company.exchange || "")}</span>
      </div>
    </div>
    <dl class="companyFacts">
      <div><dt>業種</dt><dd>${escapeHtml(company.industry || "未分類")}</dd></div>
      <div><dt>国</dt><dd>${escapeHtml(company.country || "--")}</dd></div>
      <div><dt>時価総額</dt><dd>${formatCompact(
        company.marketCapitalization,
      )}</dd></div>
    </dl>
    ${
      website
        ? `<a class="textLink" href="${escapeHtml(
            website,
          )}" target="_blank" rel="noopener noreferrer">企業サイトを開く →</a>`
        : ""
    }
  `;
}

function renderNews(news = []) {
  if (!news.length) {
    elements.newsList.innerHTML =
      '<p class="emptyState">対象ニュースがないか、ニュースAPIが未接続です。</p>';
    return;
  }

  elements.newsList.innerHTML = news
    .slice(0, 6)
    .map((item) => {
      const url = safeUrl(item.url);
      const published = item.publishedAt
        ? new Date(item.publishedAt).toLocaleString("ja-JP")
        : "--";
      const headline = escapeHtml(item.headline);

      return `
        <article class="newsItem">
          <span>${escapeHtml(item.source || "News")}・${escapeHtml(
            published,
          )}</span>
          <strong>${
            url
              ? `<a href="${escapeHtml(
                  url,
                )}" target="_blank" rel="noopener noreferrer">${headline}</a>`
              : headline
          }</strong>
        </article>
      `;
    })
    .join("");
}

function renderContext(context) {
  renderCompany(context?.company);
  renderNews(context?.news);

  const disclosures = context?.disclosures || [];
  elements.disclosureList.innerHTML = disclosures.length
    ? disclosures
        .slice(0, 6)
        .map(
          (item) =>
            `<div class="newsItem"><strong>${escapeHtml(
              item.title || item.headline,
            )}</strong></div>`,
        )
        .join("")
    : '<p class="emptyState">適時開示アダプターは未接続です。TDnet等の取得元を後から追加できます。</p>';

  elements.sentimentSummary.innerHTML = context?.sentiment
    ? `<strong>${formatNumber(
        context.sentiment.score,
        0,
      )} / 100</strong><span>${escapeHtml(
        context.sentiment.reason || "",
      )}</span>`
    : '<p class="emptyState">掲示板・X・Reddit等の投資家心理データは未接続です。</p>';
}

export function renderAnalysis(state) {
  const {
    analysis,
    indicators,
    context,
    companyName,
    symbol,
    period,
    history,
  } = state;

  elements.resultCompanyName.textContent =
    context?.company?.name || companyName || symbol;
  elements.totalScore.textContent = analysis.totalScore;
  elements.overallScoreLabel.textContent = analysis.result.label;
  elements.predictionPeriodLabel.textContent = `参考期間：${period}営業日`;
  elements.predictionBadge.textContent = analysis.result.label;
  elements.predictionBadge.className = `predictionBadge ${analysis.result.className}`;
  elements.dataCompleteness.textContent = `${analysis.availableCount} / ${analysis.totalCount}・${analysis.dataCoverage}%`;
  elements.technicalScore.textContent = finite(analysis.technicalScore)
    ? `${analysis.technicalScore} / 100`
    : "--";
  elements.dataSourceBadge.textContent = "実データ";
  elements.dataSourceDescription.textContent = `${history.candles.length}本の${history.interval}足から計算しました。未接続データは総合スコアの分母から除外しています。`;

  renderFactors(analysis.factors);
  renderReasons(analysis.factors);
  renderIndicatorSnapshot(indicators, symbol);
  renderContext(context);
}

export function setBacktestStatus(message, asHtml = false) {
  if (asHtml) {
    elements.backtestStatus.innerHTML = message;
  } else {
    elements.backtestStatus.textContent = message;
  }
}

export function setBacktestLoading(isLoading) {
  elements.runBacktestButton.disabled = isLoading;
  elements.runBacktestButton.textContent = isLoading
    ? "検証中..."
    : "過去データで検証";
}
