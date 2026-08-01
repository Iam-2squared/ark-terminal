import {
  runBrowserAlerts,
  requestBrowserNotificationPermission,
} from "./alerts.js";
import {
  DEFAULT_ALERT_SETTINGS,
  INITIAL_LIVE_SCAN_LIMIT,
} from "./config.js";
import {
  loadDiscoveryDataset,
  mergeScanResults,
  scanSymbols,
} from "./data.js";
import {
  applyScreenerFilters,
  collectFilterOptions,
} from "./filtering.js";
import {
  loadAlertSettings,
  loadWatchlist,
  saveAlertSettings,
  toggleWatchlist,
} from "./storage.js";
import {
  populateSelect,
  renderRanking,
  renderSummary,
  setLoading,
  setStatus,
} from "./ui.js";

const elements = {};
const state = {
  universe: [],
  entries: [],
  meta: {},
  watchlist: new Set(),
  scanController: null,
};

function collectElements() {
  [
    "queryFilter",
    "priceFilter",
    "budgetFilter",
    "marketFilter",
    "themeFilter",
    "marketCapFilter",
    "volumeFilter",
    "scoreFilter",
    "confidenceFilter",
    "riskFilter",
    "sortFilter",
    "watchlistOnly",
    "resetFilters",
    "refreshButton",
    "coverageCount",
    "resultCount",
    "blockedCount",
    "coverageBar",
    "coverageDescription",
    "refreshCycleCount",
    "refreshCycleBar",
    "refreshCycleDescription",
    "updatedAt",
    "rankingBody",
    "dataStatus",
    "scanStatus",
    "alertEnabled",
    "alertScore",
    "alertConfidence",
    "alertWatchlistOnly",
    "saveAlertButton",
    "notificationButton",
    "alertStatus",
  ].forEach((id) => {
    elements[id] = document.getElementById(id);
  });
}

function readFilters() {
  return {
    query: elements.queryFilter.value,
    priceBand: elements.priceFilter.value,
    budget: elements.budgetFilter.value,
    market: elements.marketFilter.value,
    theme: elements.themeFilter.value,
    marketCap: elements.marketCapFilter.value,
    minimumVolumeRatio: elements.volumeFilter.value,
    minimumScore: elements.scoreFilter.value,
    minimumConfidence: elements.confidenceFilter.value,
    risk: elements.riskFilter.value,
    sort: elements.sortFilter.value,
    watchlistOnly: elements.watchlistOnly.checked,
  };
}

function render() {
  const filtered = applyScreenerFilters(
    state.entries,
    readFilters(),
    state.watchlist,
  );

  renderSummary(elements, state.entries, filtered, state.meta);
  renderRanking(elements, filtered, state.watchlist);
}

function resetFilters() {
  elements.queryFilter.value = "";
  elements.priceFilter.value = "all";
  elements.budgetFilter.value = "";
  elements.marketFilter.value = "all";
  elements.themeFilter.value = "all";
  elements.marketCapFilter.value = "all";
  elements.volumeFilter.value = "0";
  elements.scoreFilter.value = "0";
  elements.confidenceFilter.value = "0";
  elements.riskFilter.value = "all";
  elements.sortFilter.value = "scoreDesc";
  elements.watchlistOnly.checked = false;
  render();
}

function selectedUniverseSymbols(limit = 24) {
  const filters = readFilters();
  const query = filters.query.trim().toLocaleLowerCase("ja");
  const preferred = state.universe.filter((entry) => {
    const matchesQuery =
      !query ||
      [entry.code, entry.symbol, entry.name, entry.sector, ...(entry.themes || [])]
        .join(" ")
        .toLocaleLowerCase("ja")
        .includes(query);
    const matchesMarket =
      filters.market === "all" || entry.market === filters.market;
    const matchesTheme =
      filters.theme === "all" ||
      entry.sector === filters.theme ||
      entry.themes?.includes(filters.theme);

    return matchesQuery && matchesMarket && matchesTheme;
  });

  return preferred
    .sort((first, second) => {
      const firstWatched = state.watchlist.has(first.symbol) ? 1 : 0;
      const secondWatched = state.watchlist.has(second.symbol) ? 1 : 0;

      return secondWatched - firstWatched;
    })
    .slice(0, limit)
    .map((entry) => entry.symbol);
}

async function liveScan(symbols) {
  if (!symbols.length) {
    setStatus(
      elements,
      "warning",
      "現在の市場・テーマ条件に一致する銘柄がありません。",
    );
    return;
  }

  state.scanController?.abort();
  state.scanController = new AbortController();
  setLoading(elements, true, `0 / ${symbols.length}銘柄を分析中`);
  setStatus(
    elements,
    "loading",
    "株価履歴を取得し、データ品質を通過した銘柄だけを採点しています。",
  );

  try {
    const updates = await scanSymbols({
      symbols,
      universe: state.universe,
      signal: state.scanController.signal,
      onProgress: ({ completed, total }) =>
        setLoading(elements, true, `${completed} / ${total}銘柄を分析中`),
    });

    state.entries = mergeScanResults(state.entries, updates);
    state.meta.generatedAt = new Date().toISOString();
    render();

    const analyzed = updates.filter(
      (entry) => entry.status === "analyzed",
    ).length;
    const blocked = updates.filter(
      (entry) => entry.status !== "analyzed",
    ).length;

    setStatus(
      elements,
      blocked ? "warning" : "success",
      `${analyzed}銘柄を更新しました。品質エラー・取得失敗 ${blocked}銘柄。`,
    );
    runBrowserAlerts(state.entries, state.watchlist);
  } catch (error) {
    if (error.name !== "AbortError") {
      setStatus(
        elements,
        "error",
        error.message || "ライブ分析に失敗しました。",
      );
    }
  } finally {
    setLoading(elements, false);
  }
}

function renderAlertSettings() {
  const settings = loadAlertSettings();

  elements.alertEnabled.checked = settings.enabled;
  elements.alertScore.value = settings.minimumScore;
  elements.alertConfidence.value = settings.minimumConfidence;
  elements.alertWatchlistOnly.checked = settings.watchlistOnly;
}

function saveAlerts() {
  const settings = saveAlertSettings({
    enabled: elements.alertEnabled.checked,
    minimumScore: elements.alertScore.value,
    minimumConfidence: elements.alertConfidence.value,
    watchlistOnly: elements.alertWatchlistOnly.checked,
    cooldownHours: DEFAULT_ALERT_SETTINGS.cooldownHours,
  });

  elements.alertStatus.textContent = settings.enabled
    ? "通知条件を保存しました。ページ表示・データ更新時に条件を判定します。"
    : "通知条件を保存しました（通知はオフです）。";
}

async function enableNotifications() {
  const permission = await requestBrowserNotificationPermission();

  if (permission === "granted") {
    elements.alertStatus.textContent =
      "ブラウザ通知を許可しました。条件保存後、更新時に判定します。";
    return;
  }

  elements.alertStatus.textContent =
    permission === "unsupported"
      ? "このブラウザは通知に対応していません。"
      : "ブラウザ通知は許可されていません。";
}

function bindEvents() {
  [
    elements.priceFilter,
    elements.marketFilter,
    elements.themeFilter,
    elements.marketCapFilter,
    elements.volumeFilter,
    elements.scoreFilter,
    elements.confidenceFilter,
    elements.riskFilter,
    elements.sortFilter,
    elements.watchlistOnly,
  ].forEach((element) => element.addEventListener("change", render));

  [elements.queryFilter, elements.budgetFilter].forEach((element) =>
    element.addEventListener("input", render),
  );

  elements.resetFilters.addEventListener("click", resetFilters);
  elements.refreshButton.addEventListener("click", () =>
    liveScan(selectedUniverseSymbols(24)),
  );
  elements.saveAlertButton.addEventListener("click", saveAlerts);
  elements.notificationButton.addEventListener(
    "click",
    enableNotifications,
  );
  elements.rankingBody.addEventListener("click", (event) => {
    const button = event.target.closest('[data-action="watch"]');

    if (!button) {
      return;
    }

    const row = button.closest("[data-symbol]");

    state.watchlist = toggleWatchlist(row.dataset.symbol);
    render();
  });
}

async function init() {
  collectElements();
  state.watchlist = loadWatchlist();
  renderAlertSettings();
  bindEvents();

  try {
    const dataset = await loadDiscoveryDataset();

    state.universe = dataset.universe;
    state.entries = dataset.entries;
    state.meta = dataset.meta;

    const options = collectFilterOptions(state.universe);

    populateSelect(elements.marketFilter, options.markets, "すべての市場");
    populateSelect(elements.themeFilter, options.themes, "すべての業種・テーマ");
    render();

    const analyzedCount = state.entries.filter(
      (entry) => entry.status === "analyzed",
    ).length;

    if (analyzedCount < 10) {
      setStatus(
        elements,
        "loading",
        "全市場スナップショットの初回作成前です。代表銘柄をライブ分析します。",
      );
      await liveScan(selectedUniverseSymbols(INITIAL_LIVE_SCAN_LIMIT));
    } else {
      const sourceBranch = state.meta.delivery?.sourceBranch;
      const automatic = sourceBranch === "automation/screener-data";

      setStatus(
        elements,
        "success",
        automatic
          ? "GitHub Actionsの最新データを自動取得して表示しています。"
          : "定期バッチで作成した全市場スナップショットを表示しています。",
      );
      runBrowserAlerts(state.entries, state.watchlist);
    }
  } catch (error) {
    setStatus(
      elements,
      "error",
      error.message || "スクリーナーデータを読み込めませんでした。",
    );
  }
}

init();
