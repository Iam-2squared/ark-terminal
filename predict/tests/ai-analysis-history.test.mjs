import assert from "node:assert/strict";
import test from "node:test";

import {
  AIAnalysisHistoryStore,
  appendAnalysisHistory,
  createAnalysisHistoryEntry,
  readAnalysisHistory,
  saveAnalysisHistory,
  summarizeAnalysisHistory,
} from "../analysis/ai-analysis-history.js";

function createStorage() {
  const values =
    new Map();

  return {
    getItem(key) {
      return values.has(key)
        ? values.get(key)
        : null;
    },

    setItem(
      key,
      value,
    ) {
      values.set(
        key,
        String(value),
      );
    },
  };
}

test(
  "Analysis history entry is normalized",
  () => {
    const entry =
      createAnalysisHistoryEntry({
        symbol:
          "7203.T",

        action:
          "BUY",

        score:
          "84",

        confidence:
          "88",

        executable:
          true,

        shares:
          100,
      });

    assert.equal(
      entry.symbol,
      "7203.T",
    );

    assert.equal(
      entry.score,
      84,
    );

    assert.equal(
      entry.confidence,
      88,
    );

    assert.equal(
      entry.executable,
      true,
    );

    assert.equal(
      entry.shares,
      100,
    );
  },
);

test(
  "History is appended and limited",
  () => {
    let history = [];

    for (
      let index = 0;
      index < 5;
      index++
    ) {
      history =
        appendAnalysisHistory({
          history,

          result: {
            id:
              `entry-${index}`,

            createdAt:
              `2026-08-0${index + 1}T00:00:00.000Z`,

            score:
              70 + index,
          },

          limit:
            3,
        });
    }

    assert.equal(
      history.length,
      3,
    );

    assert.equal(
      history[0].id,
      "entry-4",
    );
  },
);

test(
  "History summary is calculated",
  () => {
    const summary =
      summarizeAnalysisHistory([
        {
          score:
            80,

          confidence:
            90,

          executable:
            true,
        },

        {
          score:
            60,

          confidence:
            70,

          executable:
            false,
        },
      ]);

    assert.equal(
      summary.total,
      2,
    );

    assert.equal(
      summary.executableCount,
      1,
    );

    assert.equal(
      summary.averageScore,
      70,
    );

    assert.equal(
      summary.averageConfidence,
      80,
    );
  },
);

test(
  "History persists in storage",
  () => {
    const storage =
      createStorage();

    saveAnalysisHistory({
      storage,

      history: [
        {
          id:
            "a",
        },
      ],
    });

    const result =
      readAnalysisHistory({
        storage,
      });

    assert.equal(
      result.length,
      1,
    );

    assert.equal(
      result[0].id,
      "a",
    );
  },
);

test(
  "History store API works",
  () => {
    const storage =
      createStorage();

    const store =
      new AIAnalysisHistoryStore({
        storage,
        limit: 10,
      });

    store.add({
      symbol:
        "AAA",

      action:
        "BUY",

      score:
        80,
    });

    assert.equal(
      store.all().length,
      1,
    );

    assert.equal(
      store.summary().total,
      1,
    );

    store.clear();

    assert.equal(
      store.all().length,
      0,
    );
  },
);