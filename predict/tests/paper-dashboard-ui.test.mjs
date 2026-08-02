import test from "node:test";
import assert from "node:assert/strict";

import {
  createPaperBroker,
} from "../paper/paper-broker.js";

import {
  clearPaperDashboard,
  createPaperDashboardRoot,
  findPaperDashboardRoot,
  mountPaperDashboard,
  mountPaperDashboardById,
} from "../paper/paper-dashboard-ui.js";

function createRoot() {
  return {
    innerHTML: "",
    dataset: {},
  };
}

test(
  "Paper Dashboardをrootへ描画",
  () => {
    const root =
      createRoot();

    const result =
      mountPaperDashboard({
        root,

        broker:
          createPaperBroker(),
      });

    assert.equal(
      result.mounted,
      true,
    );

    assert.match(
      root.innerHTML,
      /仮想口座ダッシュボード/,
    );

    assert.equal(
      root.dataset.mounted,
      "true",
    );
  },
);

test(
  "root未指定は安全に失敗",
  () => {
    const result =
      mountPaperDashboard({
        root: null,
      });

    assert.equal(
      result.mounted,
      false,
    );

    assert.equal(
      result.reason,
      "missing_root",
    );
  },
);

test(
  "Dashboardをクリア",
  () => {
    const root =
      createRoot();

    root.innerHTML =
      "<p>test</p>";

    assert.equal(
      clearPaperDashboard({
        root,
      }),
      true,
    );

    assert.equal(
      root.innerHTML,
      "",
    );
  },
);

test(
  "documentからrootを検索",
  () => {
    const root =
      createRoot();

    const documentRef = {
      getElementById(id) {
        return id ===
          "paper-trading-dashboard"
          ? root
          : null;
      },
    };

    assert.equal(
      findPaperDashboardRoot({
        documentRef,
      }),
      root,
    );
  },
);

test(
  "rootを新規作成",
  () => {
    const children = [];

    const parent = {
      appendChild(node) {
        children.push(node);
      },
    };

    const documentRef = {
      getElementById() {
        return null;
      },

      createElement() {
        return {
          id: "",
          dataset: {},
          innerHTML: "",
        };
      },
    };

    const root =
      createPaperDashboardRoot({
        documentRef,
        parent,
      });

    assert.equal(
      root.id,
      "paper-trading-dashboard",
    );

    assert.equal(
      children.length,
      1,
    );
  },
);

test(
  "ID指定でDashboardを描画",
  () => {
    const root =
      createRoot();

    const documentRef = {
      getElementById() {
        return root;
      },
    };

    const result =
      mountPaperDashboardById({
        documentRef,

        broker:
          createPaperBroker(),
      });

    assert.equal(
      result.mounted,
      true,
    );

    assert.match(
      root.innerHTML,
      /Paper Trading稼働中/,
    );
  },
);