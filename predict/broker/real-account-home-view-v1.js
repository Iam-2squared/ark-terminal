import {
  normalizeReadonlyAccount,
  normalizeReadonlyPosition,
} from "./readonly-broker-normalizer.js";

export const REAL_ACCOUNT_HOME_VIEW_VERSION =
  "real-account-home-view-v1";

function textOrNull(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  return String(value);
}

function createStatus({
  connected,
  authenticated,
  synchronized,
  readyMessage = null,
} = {}) {
  if (!connected) {
    return {
      code: "not_connected",
      label: "未接続",
      tone: "warning",
      message:
        "実口座データの接続先がまだ設定されていません。",
    };
  }

  if (!authenticated) {
    return {
      code: "authentication_required",
      label: "認証待ち",
      tone: "warning",
      message:
        "実口座は検出されていますが、読み取り認証が完了していません。",
    };
  }

  if (!synchronized) {
    return {
      code: "sync_waiting",
      label: "同期待ち",
      tone: "warning",
      message:
        "接続済みですが、口座残高の同期結果はまだ届いていません。",
    };
  }

  return {
    code: "ready",
    label: "READ ONLY",
    tone: "safe",
    message:
      readyMessage ||
      "実口座データを読み取り専用で表示しています。",
  };
}

function metricIsAvailable(
  normalizedAccount,
  metric,
) {
  const availableMetrics =
    normalizedAccount?.raw?.availableMetrics;

  if (
    !availableMetrics ||
    typeof availableMetrics !== "object"
  ) {
    return true;
  }

  return availableMetrics[metric] !== false;
}

export function createRealAccountHomeView({
  connection = {},
  account = null,
  positions = [],
} = {}) {
  const connected =
    connection?.connected === true;

  const authenticated =
    connection?.authenticated === true;

  const normalizedAccount =
    account &&
    typeof account === "object"
      ? normalizeReadonlyAccount(
          account,
        )
      : null;

  const normalizedPositions =
    Array.isArray(positions)
      ? positions
          .map(
            normalizeReadonlyPosition,
          )
          .filter(
            (position) =>
              position.symbol &&
              position.quantity !== 0,
          )
      : [];

  const synchronized =
    Boolean(
      connected &&
      authenticated &&
      normalizedAccount,
    );

  const status =
    createStatus({
      connected,
      authenticated,
      synchronized,
      readyMessage:
        textOrNull(
          connection?.message,
        ),
    });

  const metric = (
    name,
    value,
  ) =>
    synchronized &&
    metricIsAvailable(
      normalizedAccount,
      name,
    )
      ? value
      : null;

  return {
    version:
      REAL_ACCOUNT_HOME_VIEW_VERSION,

    status,

    provider:
      textOrNull(
        connection?.provider ??
        normalizedAccount?.provider,
      ),

    accountType:
      normalizedAccount?.accountType ||
      null,

    currency:
      normalizedAccount?.currency ||
      "JPY",

    lastSyncAt:
      textOrNull(
        connection?.lastSyncAt ??
        normalizedAccount?.updatedAt,
      ),

    metrics: {
      equity:
        metric(
          "equity",
          normalizedAccount?.equity,
        ),

      cash:
        metric(
          "cash",
          normalizedAccount?.cash,
        ),

      buyingPower:
        metric(
          "buyingPower",
          normalizedAccount?.buyingPower,
        ),

      marketValue:
        metric(
          "marketValue",
          normalizedAccount?.marketValue,
        ),

      unrealizedPnl:
        metric(
          "unrealizedPnl",
          normalizedAccount?.unrealizedPnl,
        ),

      positionsCount:
        synchronized
          ? normalizedPositions.length
          : null,
    },

    safety: {
      readOnly: true,
      liveTradingEnabled: false,
      executionAllowed: false,
      orderCreationAllowed: false,
      orderTransmissionAllowed: false,
      orderCancellationAllowed: false,
    },
  };
}

export const RealAccountHomeViewInternals = {
  textOrNull,
  createStatus,
  metricIsAvailable,
};
