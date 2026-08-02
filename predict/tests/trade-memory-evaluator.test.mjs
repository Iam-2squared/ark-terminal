import assert from "node:assert/strict";
import test from "node:test";

import {
  evaluateTradeMemoryRecord,
  resolvePendingTradeMemory,
} from "../trading/trade-memory-evaluator.js";

function pendingRecord(overrides = {}) {
  return {
    id: "memory-1",
    symbol: "2410.T",
    status: "pending",
    decision: "approve",
    signalTime: 1_700_000_000,
    entryPrice: 100,
    stopPrice: 95,
    firstTargetPrice: 108,
    secondTargetPrice: 115,
    evaluation: {
      evaluatedAt: null,
      exitPrice: null,
      actualReturnPercent: null,
      maximumFavorableMovePercent: null,
      maximumAdverseMovePercent: null,
      hit: null,
    },
    ...overrides,
  };
}

function bar(
  seconds,
  open,
  high,
  low,
  close,
) {
  return {
    time:
      1_700_000_000 +
      seconds,
    open,
    high,
    low,
    close,
  };
}

test(
  "第一利確到達を勝ちとして解決する",
  () => {
    const result =
      evaluateTradeMemoryRecord(
        pendingRecord(),
        [
          bar(
            60,
            100,
            104,
            98,
            103,
          ),

          bar(
            120,
            103,
            109,
            101,
            108,
          ),
        ],
      );

    assert.equal(
      result.evaluated,
      true,
    );

    assert.equal(
      result.record.status,
      "resolved",
    );

    assert.equal(
      result.record
        .evaluation
        .exitReason,
      "first_target",
    );

    assert.equal(
      result.record
        .evaluation
        .exitPrice,
      108,
    );

    assert.equal(
      result.record
        .evaluation
        .hit,
      true,
    );

    assert.equal(
      Math.round(
        result.record
          .evaluation
          .actualReturnPercent,
      ),
      8,
    );
  },
);

test(
  "ストップ到達を負けとして解決する",
  () => {
    const result =
      evaluateTradeMemoryRecord(
        pendingRecord(),
        [
          bar(
            60,
            100,
            102,
            94,
            96,
          ),
        ],
      );

    assert.equal(
      result.record
        .evaluation
        .exitReason,
      "stop",
    );

    assert.equal(
      result.record
        .evaluation
        .exitPrice,
      95,
    );

    assert.equal(
      result.record
        .evaluation
        .hit,
      false,
    );

    assert.equal(
      Math.round(
        result.record
          .evaluation
          .actualReturnPercent,
      ),
      -5,
    );
  },
);

test(
  "同一足で利確とストップに触れた場合は保守的にストップを優先する",
  () => {
    const result =
      evaluateTradeMemoryRecord(
        pendingRecord(),
        [
          bar(
            60,
            100,
            110,
            94,
            106,
          ),
        ],
      );

    assert.equal(
      result.record
        .evaluation
        .exitReason,
      "stop",
    );

    assert.equal(
      result.record
        .evaluation
        .hit,
      false,
    );
  },
);

test(
  "最大本数まで未到達なら最終終値で期間終了判定する",
  () => {
    const result =
      evaluateTradeMemoryRecord(
        pendingRecord(),
        [
          bar(
            60,
            100,
            104,
            98,
            102,
          ),

          bar(
            120,
            102,
            106,
            99,
            105,
          ),
        ],
        {
          maximumBars: 2,
        },
      );

    assert.equal(
      result.record
        .evaluation
        .exitReason,
      "horizon_end",
    );

    assert.equal(
      result.record
        .evaluation
        .exitPrice,
      105,
    );

    assert.equal(
      result.record
        .evaluation
        .hit,
      true,
    );
  },
);

test(
  "waitとrejectは自動売買成績として解決しない",
  () => {
    const result =
      evaluateTradeMemoryRecord(
        pendingRecord({
          decision: "wait",
        }),
        [
          bar(
            60,
            100,
            110,
            99,
            108,
          ),
        ],
      );

    assert.equal(
      result.evaluated,
      false,
    );

    assert.equal(
      result.reason,
      "not_approved",
    );
  },
);

test(
  "銘柄別の価格履歴で未判定レコードを一括解決する",
  () => {
    const records = [
      pendingRecord(),

      pendingRecord({
        id: "memory-2",
        symbol: "7203.T",
        entryPrice: 200,
        stopPrice: 190,
        firstTargetPrice: 220,
        secondTargetPrice: 240,
      }),
    ];

    const result =
      resolvePendingTradeMemory(
        records,
        {
          "2410.T": [
            bar(
              60,
              100,
              109,
              99,
              108,
            ),
          ],

          "7203.T": [
            bar(
              60,
              200,
              205,
              189,
              192,
            ),
          ],
        },
      );

    assert.equal(
      result.resolvedCount,
      2,
    );

    assert.equal(
      result.pendingCount,
      0,
    );
  },
);