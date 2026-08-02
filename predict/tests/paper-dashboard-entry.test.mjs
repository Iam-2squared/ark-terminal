import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const entrySource =
  fs.readFileSync(
    new URL(
      "../paper/paper-dashboard-entry.js",
      import.meta.url,
    ),
    "utf8",
  );

const htmlSource =
  fs.readFileSync(
    new URL(
      "../index.html",
      import.meta.url,
    ),
    "utf8",
  );

test(
  "Paper Dashboard EntryはControllerを読み込む",
  () => {
    assert.match(
      entrySource,
      /createPaperDashboardController/,
    );

    assert.match(
      entrySource,
      /paper-dashboard-controller\.js/,
    );
  },
);

test(
  "Prediction LabにPaper Dashboard rootが存在",
  () => {
    assert.match(
      htmlSource,
      /id="paper-trading-dashboard"/,
    );

    assert.match(
      htmlSource,
      /仮想売買口座/,
    );
  },
);

test(
  "Paper Dashboard Entryをmoduleとして読込",
  () => {
    assert.match(
      htmlSource,
      /<script\s+type="module"\s+src="\.\/paper\/paper-dashboard-entry\.js"><\/script>/,
    );
  },
);

test(
  "DOMContentLoaded後にDashboardを開始",
  () => {
    assert.match(
      entrySource,
      /DOMContentLoaded/,
    );

    assert.match(
      entrySource,
      /startPaperDashboard\(\)/,
    );
  },
);

test(
  "ブラウザ操作APIを公開",
  () => {
    assert.match(
      entrySource,
      /window\.ArkPaperTrading/,
    );

    assert.match(
      entrySource,
      /submitOrder/,
    );

    assert.match(
      entrySource,
      /activateKillSwitch/,
    );
  },
);