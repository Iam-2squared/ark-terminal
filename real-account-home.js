import {
  createRealAccountHomeView,
} from "./predict/broker/real-account-home-view-v1.js";

const REMOTE_REAL_ACCOUNT_API_BASE =
  "/api/broker-readonly";

const DEFAULT_LOCAL_REAL_ACCOUNT_API_BASE =
  "http://127.0.0.1:8000/broker";

const CONNECTION_TIMEOUT_MS = 3500;
const SNAPSHOT_TIMEOUT_MS = 5000;

function getLocalApiBase() {
  const runtimeValue =
    globalThis.ARK_REAL_ACCOUNT_BRIDGE_URL;

  let storedValue = null;

  try {
    storedValue =
      globalThis.localStorage?.getItem(
        "arkRealAccountBridgeUrl",
      );
  }
  catch {
    storedValue = null;
  }

  return String(
    runtimeValue ||
    storedValue ||
    DEFAULT_LOCAL_REAL_ACCOUNT_API_BASE,
  )
    .trim()
    .replace(/\/+$/, "");
}

function ensureStylesheet() {
  if (
    document.querySelector(
      'link[data-real-account-home="true"]',
    )
  ) {
    return;
  }

  const link =
    document.createElement("link");

  link.rel = "stylesheet";
  link.href = "./real-account-home.css";
  link.dataset.realAccountHome = "true";

  document.head.appendChild(link);
}

function createCard() {
  const grid =
    document.querySelector(
      ".homeBottomGrid",
    );

  if (!grid) {
    return null;
  }

  const existing =
    document.getElementById(
      "realAccountCard",
    );

  if (existing) {
    return existing;
  }

  grid.insertAdjacentHTML(
    "beforeend",
    `
      <article
        class="dashboardCard realAccountCard"
        id="realAccountCard"
        aria-busy="true"
      >
        <div class="cardHeader homeCardHeaderSpread">
          <div class="homeTitleGroup">
            <span class="cardIcon">🏦</span>
            <div>
              <p class="homeEyebrow">Real Brokerage Account</p>
              <h2>実口座</h2>
            </div>
          </div>
          <span
            class="statusPill realAccountStatus warning"
            id="realAccountStatus"
          >確認中</span>
        </div>

        <div class="realAccountMeta">
          <span>
            接続先
            <strong id="realAccountProvider">確認中</strong>
          </span>
          <span>
            最終同期
            <strong id="realAccountSync">--</strong>
          </span>
          <span>
            保有銘柄
            <strong id="realAccountPositions">--</strong>
          </span>
        </div>

        <div class="paperMetricGrid realAccountMetricGrid">
          <div>
            <span>総資産</span>
            <strong id="realAccountEquity">--</strong>
          </div>
          <div>
            <span>現物買付可能額</span>
            <strong id="realAccountBuyingPower">--</strong>
          </div>
          <div>
            <span>保有時価</span>
            <strong id="realAccountMarketValue">--</strong>
          </div>
          <div>
            <span>評価損益</span>
            <strong id="realAccountPnl">--</strong>
          </div>
        </div>

        <div class="realAccountSafetyNotice">
          <span>🔒</span>
          <div>
            <strong>読み取り専用</strong>
            <p id="realAccountMessage">
              実口座の接続状態を確認しています。
            </p>
          </div>
        </div>
      </article>
    `,
  );

  return document.getElementById(
    "realAccountCard",
  );
}

async function fetchJson(
  apiBase,
  path,
  {
    timeoutMs = SNAPSHOT_TIMEOUT_MS,
  } = {},
) {
  const controller =
    new AbortController();

  const timeoutId =
    setTimeout(
      () => controller.abort(),
      timeoutMs,
    );

  const isSameOrigin =
    apiBase.startsWith("/");

  try {
    const response =
      await fetch(
        `${apiBase}/${path}`,
        {
          method: "GET",
          credentials:
            isSameOrigin
              ? "same-origin"
              : "omit",
          cache: "no-store",
          signal:
            controller.signal,
          headers: {
            Accept: "application/json",
            "X-Ark-Read-Only": "true",
          },
        },
      );

    const body =
      await response.json();

    if (!response.ok) {
      throw new Error(
        body?.message ||
        body?.detail ||
        `Read-only broker request failed: ${response.status}`,
      );
    }

    return body;
  }
  finally {
    clearTimeout(timeoutId);
  }
}

async function resolveConnectionSource() {
  const localApiBase =
    getLocalApiBase();

  try {
    const connection =
      await fetchJson(
        localApiBase,
        "connection",
        {
          timeoutMs:
            CONNECTION_TIMEOUT_MS,
        },
      );

    return {
      apiBase:
        localApiBase,
      connection,
      local:
        true,
    };
  }
  catch (localError) {
    console.info(
      "Local RSS account bridge is unavailable. Falling back to remote read-only status.",
      localError,
    );
  }

  const connection =
    await fetchJson(
      REMOTE_REAL_ACCOUNT_API_BASE,
      "connection",
      {
        timeoutMs:
          CONNECTION_TIMEOUT_MS,
      },
    );

  return {
    apiBase:
      REMOTE_REAL_ACCOUNT_API_BASE,
    connection,
    local:
      false,
  };
}

function formatCurrency(
  value,
  currency = "JPY",
) {
  if (
    value === null ||
    value === undefined ||
    !Number.isFinite(Number(value))
  ) {
    return "--";
  }

  return new Intl.NumberFormat(
    "ja-JP",
    {
      style: "currency",
      currency,
      maximumFractionDigits:
        currency === "JPY"
          ? 0
          : 2,
    },
  ).format(Number(value));
}

function formatSyncTime(value) {
  if (!value) {
    return "未同期";
  }

  const date =
    new Date(value);

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return "未同期";
  }

  return date.toLocaleString(
    "ja-JP",
  );
}

function setText(id, value) {
  const element =
    document.getElementById(id);

  if (element) {
    element.textContent = value;
  }
}

function render(view) {
  const card =
    document.getElementById(
      "realAccountCard",
    );

  const status =
    document.getElementById(
      "realAccountStatus",
    );

  if (!card || !status) {
    return;
  }

  status.textContent =
    view.status.label;

  status.className =
    `statusPill realAccountStatus ${view.status.tone}`;

  setText(
    "realAccountProvider",
    view.provider &&
    view.provider !== "unconfigured"
      ? view.provider
      : "未設定",
  );

  setText(
    "realAccountSync",
    formatSyncTime(
      view.lastSyncAt,
    ),
  );

  setText(
    "realAccountPositions",
    view.metrics.positionsCount === null
      ? "--"
      : `${view.metrics.positionsCount}銘柄`,
  );

  setText(
    "realAccountEquity",
    formatCurrency(
      view.metrics.equity,
      view.currency,
    ),
  );

  setText(
    "realAccountBuyingPower",
    formatCurrency(
      view.metrics.buyingPower,
      view.currency,
    ),
  );

  setText(
    "realAccountMarketValue",
    formatCurrency(
      view.metrics.marketValue,
      view.currency,
    ),
  );

  const pnlElement =
    document.getElementById(
      "realAccountPnl",
    );

  if (pnlElement) {
    pnlElement.textContent =
      formatCurrency(
        view.metrics.unrealizedPnl,
        view.currency,
      );

    pnlElement.className = "";

    if (
      view.metrics.unrealizedPnl !== null
    ) {
      pnlElement.classList.add(
        Number(
          view.metrics.unrealizedPnl,
        ) >= 0
          ? "positive"
          : "negative",
      );
    }
  }

  setText(
    "realAccountMessage",
    view.status.message,
  );

  card.dataset.connectionStatus =
    view.status.code;

  card.setAttribute(
    "aria-busy",
    "false",
  );
}

function renderError(error) {
  const card =
    document.getElementById(
      "realAccountCard",
    );

  const status =
    document.getElementById(
      "realAccountStatus",
    );

  if (status) {
    status.textContent = "取得失敗";
    status.className =
      "statusPill realAccountStatus error";
  }

  setText(
    "realAccountProvider",
    "確認できません",
  );

  setText(
    "realAccountMessage",
    "実口座データを取得できませんでした。注文機能は引き続き無効です。",
  );

  if (card) {
    card.dataset.connectionStatus =
      "error";

    card.setAttribute(
      "aria-busy",
      "false",
    );
  }

  console.error(
    "Real account read-only status load failed:",
    error,
  );
}

export async function loadRealAccountHome() {
  ensureStylesheet();

  const card =
    createCard();

  if (!card) {
    return;
  }

  try {
    const source =
      await resolveConnectionSource();

    const connection =
      source.connection;

    card.dataset.accountSource =
      source.local
        ? "local-rss-bridge"
        : "remote-readonly-status";

    if (
      connection?.connected !== true ||
      connection?.authenticated !== true
    ) {
      render(
        createRealAccountHomeView({
          connection,
        }),
      );

      return;
    }

    const [
      accountResponse,
      positionsResponse,
    ] =
      await Promise.all([
        fetchJson(
          source.apiBase,
          "account",
        ),
        fetchJson(
          source.apiBase,
          "positions",
        ),
      ]);

    render(
      createRealAccountHomeView({
        connection,
        account:
          accountResponse?.account ??
          accountResponse ??
          null,
        positions:
          positionsResponse?.positions ??
          positionsResponse ??
          [],
      }),
    );
  }
  catch (error) {
    renderError(error);
  }
}

loadRealAccountHome();

export const RealAccountHomeInternals = {
  formatCurrency,
  formatSyncTime,
  getLocalApiBase,
  resolveConnectionSource,
};
