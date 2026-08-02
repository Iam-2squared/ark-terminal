import test from "node:test";
import assert from "node:assert/strict";

import {
  assertPaperAccount,
  createPaperAccount,
  updateAccountValuation,
} from "../paper/paper-account.js";

test(
  "仮想口座を作成",
  () => {
    const account =
      createPaperAccount({
        initialCash:
          1_000_000,
      });

    assert.equal(
      account.mode,
      "paper",
    );

    assert.equal(
      account.cash,
      1_000_000,
    );

    assert.equal(
      account.equity,
      1_000_000,
    );

    assert.deepEqual(
      account.positions,
      {},
    );
  },
);

test(
  "口座評価額を更新",
  () => {
    const account =
      createPaperAccount({
        initialCash:
          1_000_000,
      });

    account.cash =
      800_000;

    const updated =
      updateAccountValuation({
        account,
        marketValue:
          230_000,
        unrealizedPnl:
          30_000,
      });

    assert.equal(
      updated.equity,
      1_030_000,
    );

    assert.equal(
      updated.totalPnl,
      30_000,
    );

    assert.equal(
      updated.totalReturnPercent,
      3,
    );
  },
);

test(
  "不正口座を拒否",
  () => {
    assert.throws(
      () =>
        assertPaperAccount({
          mode:
            "live",
          cash:
            100,
          positions: {},
        }),
      /Paper account mode/,
    );
  },
);