function finite(value) {
  if (value === null || value === undefined || value === "") {
    return false;
  }

  return Number.isFinite(Number(value));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function number(value, digits = 0) {
  if (!finite(value)) {
    return "--";
  }

  return new Intl.NumberFormat("ja-JP", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(Number(value));
}

function price(entry) {
  if (!finite(entry.currentPrice)) {
    return "--";
  }

  const prefix = entry.currency === "USD" ? "$" : "¥";

  return `${prefix}${number(entry.currentPrice, entry.currency === "USD" ? 2 : 0)}`;
}

function compactCurrency(value) {
  if (!finite(value)) {
    return "未取得";
  }

  const amount = Number(value);

  if (amount >= 1_000_000_000_000) {
    return `${number(amount / 1_000_000_000_000, 1)}兆円`;
  }

  return `${number(amount / 100_000_000, 0)}億円`;
}

function percent(value, digits = 1, signed = false) {
  if (!finite(value)) {
    return "--";
  }

  const numeric = Number(value);
  const sign = signed && numeric > 0 ? "+" : "";

  return `${sign}${number(numeric, digits)}%`;
}

function tone(value) {
  if (!finite(value) || Number(value) === 0) {
    return "neutral";
  }

  return Number(value) > 0 ? "positive" : "negative";
}

function scoreTone(score) {
  if (Number(score) >= 70) {
    return "strong";
  }

  if (Number(score) >= 55) {
    return "good";
  }

  if (Number(score) <= 40) {
    return "weak";
  }

  return "neutral";
}

export function populateSelect(select, values, allLabel) {
  select.replaceChildren();
  const all = document.createElement("option");

  all.value = "all";
  all.textContent = allLabel;
  select.append(all);

  values.forEach((value) => {
    const option = document.createElement("option");

    option.value = value;
    option.textContent = value;
    select.append(option);
  });
}

export function renderSummary(elements, entries, filtered, meta) {
  const analyzed = entries.filter((entry) => entry.status === "analyzed").length;
  const blocked = entries.filter((entry) => entry.status === "blocked").length;
  const universeCount = Number(meta.universeCount) || 0;
  const coverage = universeCount
    ? Math.round((analyzed / universeCount) * 100)
    : 0;

  elements.coverageCount.textContent = `${number(analyzed)} / ${number(
    universeCount,
  )}`;
  elements.resultCount.textContent = number(filtered.length);
  elements.blockedCount.textContent = number(blocked);
  elements.coverageBar.style.width = `${Math.min(100, coverage)}%`;
  elements.coverageDescription.textContent =
    `スコア取得済み ${number(analyzed)}銘柄（全${number(
      universeCount,
    )}銘柄中 ${coverage}%）`;

  const refreshProgress = meta.refreshProgress || {};
  const processed = Number(refreshProgress.processed) || 0;
  const refreshTotal = Number(refreshProgress.total) || universeCount;
  const refreshPercent = refreshTotal
    ? Math.round((processed / refreshTotal) * 100)
    : 0;
  const cycleNumber = Number(refreshProgress.cycleNumber) || 0;

  elements.refreshCycleCount.textContent = refreshTotal
    ? `${number(processed)} / ${number(refreshTotal)}`
    : "--";
  elements.refreshCycleBar.style.width =
    `${Math.min(100, refreshPercent)}%`;
  elements.refreshCycleDescription.textContent = refreshTotal
    ? refreshProgress.cycleComplete
      ? `第${number(cycleNumber)}サイクル完了`
      : `第${number(cycleNumber)}サイクル・${refreshPercent}%更新済み`
    : "GitHub Actionsの初回バッチ待ち";

  const updatedAt = meta.generatedAt ? new Date(meta.generatedAt) : null;

  elements.updatedAt.textContent =
    updatedAt && !Number.isNaN(updatedAt.getTime())
      ? updatedAt.toLocaleString("ja-JP")
      : "ライブ分析待ち";
}

function reasonMarkup(entry) {
  const reason = entry.reasons?.[0] || "テクニカル指標を集約した評価です。";

  return `<span class="resultReason">${escapeHtml(reason)}</span>`;
}

function themeMarkup(entry) {
  const labels = [entry.market, ...(entry.themes || []).slice(0, 2)]
    .filter(Boolean)
    .map((label) => `<span class="tag">${escapeHtml(label)}</span>`)
    .join("");

  return labels || '<span class="tag">未分類</span>';
}

export function renderRanking(elements, entries, watchlist) {
  if (!entries.length) {
    elements.rankingBody.innerHTML = `
      <tr>
        <td class="emptyState" colspan="12">
          条件に合う分析済み銘柄がありません。条件を緩めるか、ライブ更新を実行してください。
        </td>
      </tr>
    `;
    return;
  }

  elements.rankingBody.innerHTML = entries
    .map((entry, index) => {
      const watched = watchlist.has(String(entry.symbol));
      const detailUrl =
        `../predict/index.html?symbol=${encodeURIComponent(entry.symbol)}` +
        `&name=${encodeURIComponent(entry.name)}`;

      return `
        <tr data-symbol="${escapeHtml(entry.symbol)}">
          <td class="rankCell">${index + 1}</td>
          <td class="watchCell">
            <button
              class="watchButton ${watched ? "active" : ""}"
              type="button"
              data-action="watch"
              aria-label="${escapeHtml(entry.name)}をウォッチリスト${
                watched ? "から削除" : "へ追加"
              }"
              title="ウォッチリスト"
            >${watched ? "★" : "☆"}</button>
          </td>
          <td class="companyCell">
            <a href="${detailUrl}">
              <strong>${escapeHtml(entry.name)}</strong>
              <span>${escapeHtml(entry.code)}・${escapeHtml(entry.symbol)}</span>
            </a>
            <div class="tagRow">${themeMarkup(entry)}</div>
            ${reasonMarkup(entry)}
          </td>
          <td><span class="scoreBadge ${scoreTone(entry.aiScore)}">${number(
            entry.aiScore,
          )}</span></td>
          <td>
            <strong>${price(entry)}</strong>
            <span class="${tone(entry.dailyChangePercent)}">${percent(
              entry.dailyChangePercent,
              2,
              true,
            )}</span>
          </td>
          <td>
            <strong>${entry.currency === "USD" ? "--" : `¥${number(
              entry.purchaseAmount,
            )}`}</strong>
            <span>${number(entry.lotSize)}株</span>
          </td>
          <td>${compactCurrency(entry.marketCap)}</td>
          <td>
            <strong>${finite(entry.volumeRatio) ? `${number(entry.volumeRatio, 2)}倍` : "--"}</strong>
          </td>
          <td>
            <strong>${number(entry.confidence)}</strong>
            <span>${escapeHtml(entry.confidenceLabel || "--")}</span>
          </td>
          <td><strong>±${percent(entry.expectedMove, 1)}</strong></td>
          <td><span class="riskBadge risk${escapeHtml(entry.risk)}">${escapeHtml(
            entry.risk || "不明",
          )}</span></td>
          <td><a class="detailButton" href="${detailUrl}">個別分析</a></td>
        </tr>
      `;
    })
    .join("");
}

export function setLoading(elements, loading, message = "") {
  elements.refreshButton.disabled = loading;
  elements.refreshButton.textContent = loading ? "分析中…" : "候補をライブ更新";
  elements.scanStatus.hidden = !message;
  elements.scanStatus.textContent = message;
}

export function setStatus(elements, type, message) {
  elements.dataStatus.className = `dataStatus ${type}`;
  elements.dataStatus.textContent = message;
}

export const UiInternals = {
  escapeHtml,
  number,
  price,
  compactCurrency,
  percent,
  scoreTone,
};
