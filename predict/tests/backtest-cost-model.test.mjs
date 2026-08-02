import test from "node:test";
import assert from "node:assert/strict";

import {
  COST_PRESETS,
  calculateCommission,
  calculateExecutionCostBreakdown,
  calculateFillPrice,
  describeBacktestCostPolicy,
  resolveBacktestCostPolicy,
} from "../trading/backtest-cost-model.js";

test(
  "楽天証券ゼロコース相当では売買手数料が0円",
  () => {
    const commission =
      calculateCommission({
        notional: 1_000_000,
        policy: {
          costPreset:
            "rakuten_zero_cash",
        },
      });

    assert.equal(
      commission,
      0,
    );
  },
);

test(
  "楽天プリセットは保守的プリセットより往復コストが低い",
  () => {
    const rakuten =
      describeBacktestCostPolicy({
        costPreset:
          "rakuten_zero_cash",
      });

    const conservative =
      describeBacktestCostPolicy({
        costPreset:
          "conservative",
      });

    assert.equal(
      rakuten.estimatedRoundTripPercent,
      0.04,
    );

    assert.ok(
      Math.abs(
        conservative.estimatedRoundTripPercent - 0.3
      ) < 1e-9,
    );

    assert.ok(
      rakuten.estimatedRoundTripPercent <
        conservative.estimatedRoundTripPercent,
    );
  },
);

test(
  "買いエントリー価格にはスプレッドとスリッページを不利に反映",
  () => {
    const fillPrice =
      calculateFillPrice({
        referencePrice: 1_000,
        side: "long",
        phase: "entry",
        policy: {
          costPreset:
            "rakuten_zero_cash",
        },
      });

    assert.ok(
      Math.abs(fillPrice - 1000.2) < 1e-9,
    );
  },
);

test(
  "買い決済価格にはスプレッドとスリッページを不利に反映",
  () => {
    const fillPrice =
      calculateFillPrice({
        referencePrice: 1_000,
        side: "long",
        phase: "exit",
        policy: {
          costPreset:
            "rakuten_zero_cash",
        },
      });

    assert.ok(
      Math.abs(fillPrice - 999.8) < 1e-9,
    );
  },
);

test(
  "個別指定値はプリセット値を上書きできる",
  () => {
    const resolved =
      resolveBacktestCostPolicy({
        costPreset:
          "rakuten_zero_cash",

        spreadPercent: 0.08,
        slippagePercentPerSide:
          0.03,
      });

    assert.equal(
      resolved.commissionPercentPerSide,
      0,
    );

    assert.equal(
      resolved.spreadPercent,
      0.08,
    );

    assert.equal(
      resolved.slippagePercentPerSide,
      0.03,
    );
  },
);

test(
  "コスト内訳を手数料と約定コストに分離",
  () => {
    const breakdown =
      calculateExecutionCostBreakdown({
        entryReferencePrice: 1_000,
        entryFillPrice: 1_001,
        exitReferencePrice: 1_100,
        exitFillPrice: 1_099,
        quantity: 100,
        entryCommission: 0,
        exitCommission: 0,
      });

    assert.deepEqual(
      breakdown,
      {
        commissionCost: 0,
        executionCost: 200,
        totalTradingCost: 200,
      },
    );
  },
);

test(
  "完全ゼロコストプリセットでは参照価格と約定価格が一致",
  () => {
    assert.equal(
      calculateFillPrice({
        referencePrice: 2_500,
        side: "long",
        phase: "entry",
        policy: {
          costPreset:
            COST_PRESETS.zero_cost.id,
        },
      }),
      2_500,
    );
  },
);


