function finiteNumber(
  value,
  fallback = 0,
) {
  const parsed =
    Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : fallback;
}

function escapeCsv(value) {
  const text =
    String(value ?? "");

  if (
    text.includes(",") ||
    text.includes('"') ||
    text.includes("\n")
  ) {
    return `"${text.replaceAll(
      '"',
      '""',
    )}"`;
  }

  return text;
}

export function normalizeHistoryForExport(
  history = [],
) {
  const safeHistory =
    Array.isArray(history)
      ? history
      : [];

  return safeHistory.map(
    (item) => ({
      id:
        item.id ?? "",

      createdAt:
        item.createdAt ?? "",

      symbol:
        item.symbol ?? "",

      action:
        item.action ?? "HOLD",

      score:
        finiteNumber(
          item.score,
          50,
        ),

      confidence:
        finiteNumber(
          item.confidence,
          0,
        ),

      agreementRate:
        finiteNumber(
          item.agreementRate,
          0,
        ),

      executable:
        item.executable === true,

      shares:
        finiteNumber(
          item.shares,
          0,
        ),

      entryPrice:
        finiteNumber(
          item.entryPrice,
          0,
        ),

      stopPrice:
        finiteNumber(
          item.stopPrice,
          0,
        ),

      targetPrice:
        finiteNumber(
          item.targetPrice,
          0,
        ),

      estimatedCost:
        finiteNumber(
          item.estimatedCost,
          0,
        ),

      buyFactors:
        Array.isArray(
          item.buyFactors,
        )
          ? item.buyFactors.join(" | ")
          : "",

      riskFactors:
        Array.isArray(
          item.riskFactors,
        )
          ? item.riskFactors.join(" | ")
          : "",
    }),
  );
}

export function exportHistoryAsJson(
  history = [],
) {
  const normalized =
    normalizeHistoryForExport(
      history,
    );

  return JSON.stringify(
    {
      version:
        "ark-analysis-history-export-v1",

      generatedAt:
        new Date().toISOString(),

      count:
        normalized.length,

      history:
        normalized,
    },
    null,
    2,
  );
}

export function exportHistoryAsCsv(
  history = [],
) {
  const normalized =
    normalizeHistoryForExport(
      history,
    );

  const headers = [
    "id",
    "createdAt",
    "symbol",
    "action",
    "score",
    "confidence",
    "agreementRate",
    "executable",
    "shares",
    "entryPrice",
    "stopPrice",
    "targetPrice",
    "estimatedCost",
    "buyFactors",
    "riskFactors",
  ];

  const rows =
    normalized.map(
      (item) =>
        headers
          .map(
            (header) =>
              escapeCsv(
                item[header],
              ),
          )
          .join(","),
    );

  return [
    headers.join(","),
    ...rows,
  ].join("\n");
}

export function createHistoryExportFile({
  history = [],
  format = "json",
  fileNamePrefix =
    "ark-analysis-history",
} = {}) {
  const normalizedFormat =
    String(format)
      .toLowerCase();

  const isCsv =
    normalizedFormat === "csv";

  const content =
    isCsv
      ? exportHistoryAsCsv(
          history,
        )
      : exportHistoryAsJson(
          history,
        );

  const extension =
    isCsv
      ? "csv"
      : "json";

  const mimeType =
    isCsv
      ? "text/csv;charset=utf-8"
      : "application/json;charset=utf-8";

  const date =
    new Date()
      .toISOString()
      .slice(0, 10);

  return {
    content,

    extension,

    mimeType,

    fileName:
      `${fileNamePrefix}-${date}.${extension}`,
  };
}

export function downloadHistoryExport({
  history = [],
  format = "json",
  documentRef =
    globalThis.document,

  URLRef =
    globalThis.URL,

  BlobRef =
    globalThis.Blob,
} = {}) {
  if (
    !documentRef ||
    !URLRef ||
    typeof BlobRef !==
      "function"
  ) {
    return {
      downloaded:
        false,

      reason:
        "browser_environment_unavailable",
    };
  }

  const file =
    createHistoryExportFile({
      history,
      format,
    });

  const blob =
    new BlobRef(
      [
        "\uFEFF",
        file.content,
      ],
      {
        type:
          file.mimeType,
      },
    );

  const url =
    URLRef.createObjectURL(
      blob,
    );

  const anchor =
    documentRef.createElement(
      "a",
    );

  anchor.href =
    url;

  anchor.download =
    file.fileName;

  anchor.hidden =
    true;

  documentRef.body?.appendChild(
    anchor,
  );

  anchor.click();

  anchor.remove?.();

  URLRef.revokeObjectURL(
    url,
  );

  return {
    downloaded:
      true,

    fileName:
      file.fileName,

    format:
      file.extension,
  };
}

export function installHistoryExportApi({
  windowRef =
    globalThis.window,
} = {}) {
  if (!windowRef) {
    return false;
  }

  windowRef
    .ArkAIAnalysisHistoryExport = {
      json() {
        return downloadHistoryExport({
          history:
            windowRef
              .__ARK_ANALYSIS_HISTORY__ ??
            [],

          format:
            "json",
        });
      },

      csv() {
        return downloadHistoryExport({
          history:
            windowRef
              .__ARK_ANALYSIS_HISTORY__ ??
            [],

          format:
            "csv",
        });
      },

      create({
        format = "json",
      } = {}) {
        return createHistoryExportFile({
          history:
            windowRef
              .__ARK_ANALYSIS_HISTORY__ ??
            [],

          format,
        });
      },
    };

  return true;
}

export const AIAnalysisHistoryExportInternals = {
  escapeCsv,
  finiteNumber,
};