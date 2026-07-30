import {
  getTradingViewSymbol,
  isJapaneseSymbol,
  normalizeSymbol,
} from "./symbols.js";

const LIGHTWEIGHT_CHARTS_URL =
  "https://cdn.jsdelivr.net/npm/lightweight-charts@5.0.8/dist/lightweight-charts.standalone.production.js";

let activeSymbol = "";
let host = null;
let latestHistory = null;
let libraryPromise = null;
let lightweightChart = null;
let resizeObserver = null;

function showChartMessage(className, message) {
  host.replaceChildren();

  const state = document.createElement("div");
  state.className = className;
  state.textContent = message;
  host.appendChild(state);
}

function destroyLightweightChart() {
  resizeObserver?.disconnect();
  resizeObserver = null;

  lightweightChart?.remove();
  lightweightChart = null;
}

function renderTradingView(symbol) {
  destroyLightweightChart();
  host.innerHTML = "";

  const container = document.createElement("div");
  container.className = "tradingview-widget-container";

  const widget = document.createElement("div");
  widget.className = "tradingview-widget-container__widget";

  const script = document.createElement("script");
  script.type = "text/javascript";
  script.src =
    "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
  script.async = true;
  script.textContent = JSON.stringify({
    autosize: true,
    symbol: getTradingViewSymbol(symbol),
    interval: "5",
    timezone: "Asia/Tokyo",
    theme: "dark",
    style: "2",
    locale: "ja",
    backgroundColor: "#0d1422",
    gridColor: "rgba(255, 255, 255, 0.05)",
    hide_top_toolbar: false,
    hide_legend: false,
    withdateranges: true,
    save_image: false,
    calendar: false,
    studies: ["STD;Volume"],
    support_host: "https://www.tradingview.com",
  });

  container.append(widget, script);
  host.appendChild(container);
}

function loadLightweightCharts() {
  if (window.LightweightCharts) {
    return Promise.resolve(window.LightweightCharts);
  }

  if (!libraryPromise) {
    libraryPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = LIGHTWEIGHT_CHARTS_URL;
      script.async = true;
      script.onload = () => resolve(window.LightweightCharts);
      script.onerror = () =>
        reject(new Error("日本株チャートライブラリを読み込めませんでした。"));
      document.head.appendChild(script);
    });
  }

  return libraryPromise;
}

function dateString(time) {
  return new Date(Number(time) * 1000).toISOString().slice(0, 10);
}

function movingAverageSeries(candles, period) {
  const values = [];
  let rolling = 0;

  candles.forEach((candle, index) => {
    rolling += candle.close;

    if (index >= period) {
      rolling -= candles[index - period].close;
    }

    if (index >= period - 1) {
      values.push({
        time: dateString(candle.time),
        value: rolling / period,
      });
    }
  });

  return values;
}

function addSeries(chart, type, options) {
  const library = window.LightweightCharts;
  const legacyMethod = {
    candlestick: "addCandlestickSeries",
    histogram: "addHistogramSeries",
    line: "addLineSeries",
  }[type];

  if (typeof chart[legacyMethod] === "function") {
    return chart[legacyMethod](options);
  }

  const definition = {
    candlestick: library.CandlestickSeries,
    histogram: library.HistogramSeries,
    line: library.LineSeries,
  }[type];

  return chart.addSeries(definition, options);
}

function configureJapaneseSeries(chart, candles) {
  const candleSeries = addSeries(chart, "candlestick", {
    upColor: "#34c759",
    downColor: "#ff453a",
    borderVisible: false,
    wickUpColor: "#34c759",
    wickDownColor: "#ff453a",
  });

  candleSeries.setData(
    candles.map((candle) => ({
      time: dateString(candle.time),
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    })),
  );

  const ma5 = addSeries(chart, "line", {
    color: "#34c759",
    lineWidth: 1,
    title: "5MA",
    visible: false,
  });
  ma5.setData(movingAverageSeries(candles, 5));

  const ma25 = addSeries(chart, "line", {
    color: "#4f7cff",
    lineWidth: 2,
    title: "25MA",
  });
  ma25.setData(movingAverageSeries(candles, 25));

  const ma75 = addSeries(chart, "line", {
    color: "#ff9f0a",
    lineWidth: 2,
    title: "75MA",
  });
  ma75.setData(movingAverageSeries(candles, 75));

  const ma200 = addSeries(chart, "line", {
    color: "#b783ff",
    lineWidth: 1,
    title: "200MA",
    visible: false,
  });
  ma200.setData(movingAverageSeries(candles, 200));

  const volume = addSeries(chart, "histogram", {
    priceFormat: { type: "volume" },
    priceScaleId: "",
  });
  volume.priceScale().applyOptions({
    scaleMargins: { top: 0.78, bottom: 0 },
  });
  volume.setData(
    candles.map((candle) => ({
      time: dateString(candle.time),
      value: candle.volume,
      color:
        candle.close >= candle.open
          ? "rgba(52,199,89,0.35)"
          : "rgba(255,69,58,0.35)",
    })),
  );

  return {
    ma5,
    ma25,
    ma75,
    ma200,
    volume,
  };
}

function setVisibleDays(chart, candles, days) {
  if (!days || days >= candles.length) {
    chart.timeScale().fitContent();
    return;
  }

  const startIndex = Math.max(0, candles.length - days);

  chart.timeScale().setVisibleRange({
    from: dateString(candles[startIndex].time),
    to: dateString(candles.at(-1).time),
  });
}

function createJapaneseControls(chart, candles, series) {
  const controls = document.createElement("div");
  controls.className = "lightweightChartControls";
  controls.setAttribute("aria-label", "日本株チャート操作");

  [
    ["1か月", 22],
    ["3か月", 66],
    ["6か月", 132],
    ["1年", 252],
    ["2年", null],
  ].forEach(([label, days]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `chartControlButton ${days === null ? "active" : ""}`;
    button.dataset.chartRange = String(days ?? "all");
    button.textContent = label;
    button.addEventListener("click", () => {
      controls
        .querySelectorAll("[data-chart-range]")
        .forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      setVisibleDays(chart, candles, days);
    });
    controls.appendChild(button);
  });

  [
    ["5MA", series.ma5, false],
    ["25MA", series.ma25, true],
    ["75MA", series.ma75, true],
    ["200MA", series.ma200, false],
    ["出来高", series.volume, true],
  ].forEach(([label, targetSeries, initiallyVisible]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `chartControlButton ${initiallyVisible ? "active" : ""}`;
    button.textContent = label;
    button.setAttribute("aria-pressed", String(initiallyVisible));
    button.addEventListener("click", () => {
      const visible = button.getAttribute("aria-pressed") !== "true";
      button.setAttribute("aria-pressed", String(visible));
      button.classList.toggle("active", visible);
      targetSeries.applyOptions({ visible });
    });
    controls.appendChild(button);
  });

  return controls;
}

async function renderJapaneseChart(symbol, candles) {
  destroyLightweightChart();
  showChartMessage("chartLoading", "日本株チャートを読み込んでいます。");

  try {
    await loadLightweightCharts();
    host.innerHTML = "";

    const controls = document.createElement("div");
    controls.className = "lightweightChartControlsPlaceholder";

    const chartElement = document.createElement("div");
    chartElement.className = "lightweightChartHost";
    host.append(controls, chartElement);

    lightweightChart = window.LightweightCharts.createChart(chartElement, {
      width: chartElement.clientWidth,
      height: chartElement.clientHeight,
      layout: {
        background: { color: "#0d1422" },
        textColor: "#8995b3",
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: "rgba(255,255,255,0.04)" },
      },
      rightPriceScale: {
        borderColor: "rgba(255,255,255,0.08)",
      },
      timeScale: {
        borderColor: "rgba(255,255,255,0.08)",
        timeVisible: false,
      },
    });

    const series = configureJapaneseSeries(lightweightChart, candles);
    controls.replaceWith(
      createJapaneseControls(lightweightChart, candles, series),
    );
    lightweightChart.timeScale().fitContent();

    resizeObserver = new ResizeObserver(() => {
      lightweightChart?.applyOptions({
        width: chartElement.clientWidth,
        height: chartElement.clientHeight,
      });
    });
    resizeObserver.observe(chartElement);

    const badge = document.createElement("div");
    badge.className = "chartProviderBadge";
    badge.textContent = `${symbol}・TradingView Lightweight Charts`;
    host.appendChild(badge);
  } catch (error) {
    showChartMessage(
      "chartError",
      error instanceof Error
        ? error.message
        : "日本株チャートを表示できませんでした。",
    );
  }
}

export function renderMarketChart(symbolValue, hostElement) {
  activeSymbol = normalizeSymbol(symbolValue);
  host = hostElement;

  if (!activeSymbol) {
    showChartMessage("chartError", "銘柄コードを入力してください。");
    return;
  }

  if (!isJapaneseSymbol(activeSymbol)) {
    renderTradingView(activeSymbol);
    return;
  }

  if (latestHistory?.symbol === activeSymbol && latestHistory.candles?.length) {
    renderJapaneseChart(activeSymbol, latestHistory.candles);
    return;
  }

  showChartMessage("chartLoading", "日本株の履歴データを待っています。");
}

export function setMarketChartHistory(history) {
  latestHistory = history;
  const symbol = normalizeSymbol(history?.symbol);

  if (
    host &&
    symbol === activeSymbol &&
    isJapaneseSymbol(symbol) &&
    history.candles?.length
  ) {
    renderJapaneseChart(symbol, history.candles);
  }
}

export function clearMarketChartHistory() {
  latestHistory = null;
}

export function destroyMarketChart() {
  destroyLightweightChart();
  host = null;
}
