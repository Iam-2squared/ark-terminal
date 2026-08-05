import test from "node:test";
import assert from "node:assert/strict";

import {
  createRealAccountHomeView,
} from "../broker/real-account-home-view-v1.js";

test(
  "未接続の実口座は金額をゼロで偽装しない",
  () => {
    const view =
      createRealAccountHomeView({
        connection: {
          connected: false,
          authenticated: false,
          provider: "unconfigured",
        },
      });

    assert.equal(
      view.status.code,
      "not_connected",
    );

    assert.equal(
      view.metrics.equity,
      null,
    );

    assert.equal(
      view.metrics.cash,
      null,
    );

    assert.equal(
      view.metrics.positionsCount,
      null,
    );
  },
);

test(
  "接続・認証・同期後だけ実口座指標を表示する",
  () => {
    const view =
      createRealAccountHomeView({
        connection: {
          connected: true,
          authenticated: true,
          provider: "rakuten-readonly",
          lastSyncAt: "2026-08-05T12:00:00.000Z",
        },
        account: {
          accountId: "SENSITIVE-ACCOUNT-ID",
          currency: "JPY",
          cash: 120000,
          buyingPower: 100000,
          marketValue: 80000,
          equity: 200000,
          unrealizedPnl: 5000,
        },
        positions: [
          {
            symbol: "7203.T",
            quantity: 100,
            marketPrice: 800,
          },
          {
            symbol: "ZERO.T",
            quantity: 0,
          },
        ],
      });

    assert.equal(
      view.status.code,
      "ready",
    );

    assert.equal(
      view.metrics.equity,
      200000,
    );

    assert.equal(
      view.metrics.cash,
      120000,
    );

    assert.equal(
      view.metrics.buyingPower,
      100000,
    );

    assert.equal(
      view.metrics.marketValue,
      80000,
    );

    assert.equal(
      view.metrics.unrealizedPnl,
      5000,
    );

    assert.equal(
      view.metrics.positionsCount,
      1,
    );

    assert.equal(
      JSON.stringify(view).includes(
        "SENSITIVE-ACCOUNT-ID",
      ),
      false,
    );
  },
);

test(
  "MARKETSPEED native RSSで取得不能な指標はゼロ表示しない",
  () => {
    const view =
      createRealAccountHomeView({
        connection: {
          connected: true,
          authenticated: true,
          provider: "MARKETSPEED II RSS / Excel",
          message:
            "MARKETSPEED II RSSの保有銘柄一覧と現物買付可能額を読み取り専用で同期しています。",
        },
        account: {
          currency: "JPY",
          cash: null,
          buyingPower: 118000,
          marketValue: 235000,
          equity: null,
          unrealizedPnl: 5000,
          availableMetrics: {
            cash: false,
            buyingPower: true,
            marketValue: true,
            equity: false,
            unrealizedPnl: true,
          },
        },
        positions: [
          {
            symbol: "4755.T",
            quantity: 100,
          },
          {
            symbol: "9432.T",
            quantity: 1000,
          },
        ],
      });

    assert.equal(
      view.metrics.equity,
      null,
    );
    assert.equal(
      view.metrics.cash,
      null,
    );
    assert.equal(
      view.metrics.buyingPower,
      118000,
    );
    assert.equal(
      view.metrics.marketValue,
      235000,
    );
    assert.equal(
      view.metrics.unrealizedPnl,
      5000,
    );
    assert.equal(
      view.status.message.includes(
        "現物買付可能額",
      ),
      true,
    );
  },
);

test(
  "接続済みでも口座スナップショットがなければ同期待ち",
  () => {
    const view =
      createRealAccountHomeView({
        connection: {
          connected: true,
          authenticated: true,
          provider: "rakuten-readonly",
        },
        account: null,
        positions: [],
      });

    assert.equal(
      view.status.code,
      "sync_waiting",
    );

    assert.equal(
      view.metrics.equity,
      null,
    );
  },
);

test(
  "Home実口座ビューは常に読み取り専用で注文機能を持たない",
  () => {
    const view =
      createRealAccountHomeView();

    assert.equal(
      view.safety.readOnly,
      true,
    );

    assert.equal(
      view.safety.liveTradingEnabled,
      false,
    );

    assert.equal(
      view.safety.executionAllowed,
      false,
    );

    assert.equal(
      view.safety.orderCreationAllowed,
      false,
    );

    assert.equal(
      view.safety.orderTransmissionAllowed,
      false,
    );

    assert.equal(
      view.safety.orderCancellationAllowed,
      false,
    );
  },
);
