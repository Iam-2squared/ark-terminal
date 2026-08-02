import test from "node:test";
import assert from "node:assert/strict";

import {
  createPaperBroker,
} from "../paper/paper-broker.js";

import {
  createPaperDashboardViewModel,
  renderPaperDashboardHtml,
} from "../paper/paper-dashboard-presenter.js";

test(
  "空のPaper口座を表示モデルへ変換",
  () => {
    const broker =
      createPaperBroker({
        initialCash:
          1_000_000,
      });

    const view =
      createPaperDashboardViewModel({
        broker,
      });

    assert.equal(
      view.status,
      "active",
    );

    assert.equal(
      view.snapshot.equity,
      1_000_000,
    );

    assert.equal(
      view.positions.length,
      0,
    );

    assert.equal(
      view.openOrders.length,
      0,
    );

    assert.ok(
      view.cards.length >= 10,
    );
  },
);

test(
  "Kill Switchを停止表示",
  () => {
    const view =
      createPaperDashboardViewModel({
        broker:
          createPaperBroker(),

        killSwitch: {
          enabled: true,
        },
      });

    assert.equal(
      view.status,
      "stopped",
    );

    assert.equal(
      view.statusLabel,
      "緊急停止中",
    );

    assert.ok(
      view.warnings.some(
        (row) =>
          row.code ===
          "KILL_SWITCH",
      ),
    );
  },
);

test(
  "HTMLへ主要UIを描画",
  () => {
    const html =
      renderPaperDashboardHtml({
        broker:
          createPaperBroker(),
      });

    assert.match(
      html,
      /仮想口座ダッシュボード/,
    );

    assert.match(
      html,
      /総資産/,
    );

    assert.match(
      html,
      /買付余力/,
    );

    assert.match(
      html,
      /保有銘柄/,
    );

    assert.match(
      html,
      /未約定注文/,
    );
  },
);