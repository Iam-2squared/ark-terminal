import { QUOTE_REFRESH_MS, SYMBOL_INPUT_DEBOUNCE_MS } from "./config.js";
import { fetchQuote } from "./data.js";
import {
  clearMarketChartHistory,
  destroyMarketChart,
  renderMarketChart,
  setMarketChartHistory,
} from "./charts.js";
import { formatPrice, normalizeSymbol } from "./symbols.js";

const elements = {};

let refreshTimer = null;
let inputTimer = null;
let requestController = null;
let activeSymbol = "";

function collectElements() {
  [
    "stockSymbol",
    "runPredictionButton",
    "refreshMarketButton",
    "marketSymbolLabel",
    "marketStatusBadge",
    "marketPrice",
    "marketChange",
    "marketChangePercent",
    "marketHigh",
    "marketLow",
    "marketVolume",
    "marketUpdatedAt",
    "marketError",
    "tradingviewChart",
  ].forEach((id) => {
    elements[id] = document.getElementById(id);
  });
}

function formatSigned(value, suffix = "") {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "--";
  }

  return (
    `${number > 0 ? "+" : ""}` +
    number.toLocaleString("ja-JP", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }) +
    suffix
  );
}

function formatVolume(value) {
  const number = Number(value);

  return Number.isFinite(number)
    ? new Intl.NumberFormat("ja-JP", {
        notation: "compact",
        maximumFractionDigits: 2,
      }).format(number)
    : "--";
}

function formatTime(value) {
  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? "--"
    : date.toLocaleTimeString("ja-JP", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
}

function setStatus(label, state) {
  elements.marketStatusBadge.textContent = label;
  elements.marketStatusBadge.className = `marketStatusBadge ${state}`;
}

function clearError() {
  elements.marketError.hidden = true;
  elements.marketError.textContent = "";
}

function showError(message) {
  elements.marketError.hidden = false;
  elements.marketError.textContent = message;
  setStatus("通信エラー", "error");
}

function clearQuoteValues() {
  [
    "marketPrice",
    "marketChange",
    "marketChangePercent",
    "marketHigh",
    "marketLow",
    "marketVolume",
    "marketUpdatedAt",
  ].forEach((key) => {
    elements[key].textContent = "--";
  });

  elements.marketChange.className = "";
  elements.marketChangePercent.className = "";
}

function renderQuote(quote, symbol) {
  const direction =
    Number(quote.change) > 0
      ? "positive"
      : Number(quote.change) < 0
        ? "negative"
        : "neutral";

  elements.marketPrice.textContent = formatPrice(quote.price, symbol);
  elements.marketChange.textContent = formatSigned(quote.change);
  elements.marketChange.className = direction;
  elements.marketChangePercent.textContent = formatSigned(
    quote.changePercent,
    "%",
  );
  elements.marketChangePercent.className = direction;
  elements.marketHigh.textContent = formatPrice(quote.high, symbol);
  elements.marketLow.textContent = formatPrice(quote.low, symbol);
  elements.marketVolume.textContent = formatVolume(quote.volume);
  elements.marketUpdatedAt.textContent = formatTime(quote.updatedAt);
}

async function updateQuote({ clear = false } = {}) {
  const symbol = normalizeSymbol(elements.stockSymbol.value);

  if (!symbol) {
    clearQuoteValues();
    showError("銘柄コードを入力してください。");
    return;
  }

  requestController?.abort();
  requestController = new AbortController();

  clearError();
  setStatus("読み込み中", "loading");
  elements.marketSymbolLabel.textContent = symbol;
  elements.refreshMarketButton.disabled = true;

  if (clear) {
    clearQuoteValues();
  }

  try {
    const quote = await fetchQuote(symbol, requestController.signal);
    renderQuote(quote, symbol);
    clearError();
    setStatus("LIVE", "live");
  } catch (error) {
    if (error.name !== "AbortError") {
      console.error("Market quote:", error);
      showError(error.message || "株価の取得に失敗しました。");
    }
  } finally {
    elements.refreshMarketButton.disabled = false;
  }
}

function stopRefresh() {
  if (refreshTimer) {
    window.clearInterval(refreshTimer);
    refreshTimer = null;
  }
}

function startMarket({ forceChart = false } = {}) {
  const symbol = normalizeSymbol(elements.stockSymbol.value);
  const changed = symbol !== activeSymbol;

  if (changed) {
    clearMarketChartHistory();
  }

  if (changed || forceChart) {
    activeSymbol = symbol;
    renderMarketChart(symbol, elements.tradingviewChart);
  }

  stopRefresh();
  updateQuote({ clear: changed });

  if (symbol && !document.hidden) {
    refreshTimer = window.setInterval(updateQuote, QUOTE_REFRESH_MS);
  }
}

function scheduleMarket() {
  window.clearTimeout(inputTimer);
  inputTimer = window.setTimeout(
    () => startMarket({ forceChart: true }),
    SYMBOL_INPUT_DEBOUNCE_MS,
  );
}

export function setMarketHistory(history) {
  setMarketChartHistory(history);
}

export function initMarket() {
  collectElements();

  elements.stockSymbol.addEventListener("input", scheduleMarket);
  elements.stockSymbol.addEventListener("change", () =>
    startMarket({ forceChart: true }),
  );
  elements.stockSymbol.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      startMarket({ forceChart: true });
    }
  });
  elements.refreshMarketButton.addEventListener("click", () =>
    startMarket({ forceChart: true }),
  );
  elements.runPredictionButton.addEventListener("click", () =>
    startMarket({ forceChart: true }),
  );

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      stopRefresh();
    } else {
      startMarket();
    }
  });

  window.addEventListener("pagehide", () => {
    stopRefresh();
    destroyMarketChart();
    requestController?.abort();
  });

  startMarket({ forceChart: true });
}
