import assert from "node:assert/strict";
import test from "node:test";

import {
  createHistoryExportFile,
  exportHistoryAsCsv,
  exportHistoryAsJson,
  normalizeHistoryForExport,
} from "../analysis/ai-analysis-history-export.js";

function sampleHistory() {
  return [
    {
      id:
        "analysis-1",

      createdAt:
        "2026-08-02T00:00:00.000Z",

      symbol:
        "7203.T",

      action:
        "BUY",

      score:
        84,

      confidence:
        88,

      agreementRate:
        75,

      executable:
        true,

      shares:
        100,

      entryPrice:
        1000,

      stopPrice:
        950,

      targetPrice:
        1100,

      estimatedCost:
        100000,

      buyFactors: [
        "上昇トレンド",
        "出来高増加",
      ],

      riskFactors: [
        "決算接近",
      ],
    },
  ];
}

test(
  "History export normalization",
  () => {
    const result =
      normalizeHistoryForExport(
        sampleHistory(),
      );

    assert.equal(
      result.length,
      1,
    );

    assert.equal(
      result[0].symbol,
      "7203.T",
    );

    assert.equal(
      result[0].buyFactors,
      "上昇トレンド | 出来高増加",
    );

    assert.equal(
      result[0].executable,
      true,
    );
  },
);

test(
  "History exports as JSON",
  () => {
    const json =
      exportHistoryAsJson(
        sampleHistory(),
      );

    const parsed =
      JSON.parse(json);

    assert.equal(
      parsed.version,
      "ark-analysis-history-export-v1",
    );

    assert.equal(
      parsed.count,
      1,
    );

    assert.equal(
      parsed.history[0].symbol,
      "7203.T",
    );
  },
);

test(
  "History exports as CSV",
  () => {
    const csv =
      exportHistoryAsCsv(
        sampleHistory(),
      );

    assert.ok(
      csv.includes(
        "symbol",
      ),
    );

    assert.ok(
      csv.includes(
        "7203.T",
      ),
    );

    assert.ok(
      csv.includes(
        "上昇トレンド | 出来高増加",
      ),
    );
  },
);

test(
  "Export file metadata is built",
  () => {
    const file =
      createHistoryExportFile({
        history:
          sampleHistory(),

        format:
          "csv",
      });

    assert.equal(
      file.extension,
      "csv",
    );

    assert.equal(
      file.mimeType,
      "text/csv;charset=utf-8",
    );

    assert.ok(
      file.fileName.endsWith(
        ".csv",
      ),
    );
  },
);

test(
  "Unknown format defaults to JSON",
  () => {
    const file =
      createHistoryExportFile({
        history: [],
        format:
          "unknown",
      });

    assert.equal(
      file.extension,
      "json",
    );

    assert.ok(
      file.fileName.endsWith(
        ".json",
      ),
    );
  },
);