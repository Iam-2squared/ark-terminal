import {
  analyzeTradeMemoryLearning,
} from "./trade-memory-learning.js";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function round(value, digits = 1) {
  if (!finite(value)) {
    return null;
  }

  const factor =
    10 ** digits;

  return (
    Math.round(
      Number(value) * factor,
    ) / factor
  );
}

function percent(value) {
  if (!finite(value)) {
    return "--";
  }

  const number =
    round(value, 1);

  const sign =
    number > 0
      ? "+"
      : "";

  return `${sign}${number}%`;
}

function weight(value) {
  if (!finite(value)) {
    return "--";
  }

  return Number(value)
    .toFixed(2);
}

const LABELS = {
  movingAverage:
    "移動平均",

  rsi:
    "RSI",

  macd:
    "MACD",

  adx:
    "ADX",

  volume:
    "出来高",

  setupStrength:
    "セットアップ強度",

  dataQuality:
    "データ品質",

  marketEnvironment:
    "市場環境",
};

export function createTradeMemoryLearningViewModel(
  records,
  baseWeights = {},
) {
  const learning =
    analyzeTradeMemoryLearning(
      records,
      baseWeights,
    );

  const rows =
    Object.entries(
      learning.metrics || {},
    )
      .map(
        ([
          key,
          metric,
        ]) => {
          const delta =
            finite(metric.suggestedWeight) &&
            finite(metric.baseWeight)
              ? Number(
                  metric.suggestedWeight,
                ) -
                Number(
                  metric.baseWeight,
                )
              : null;

          return {
            key,

            label:
              LABELS[key] ||
              key,

            sampleSize:
              metric.sampleSize,

            winRate:
              metric.winRate,

            averageReturnPercent:
              metric.averageReturnPercent,

            averageFavorableMovePercent:
              metric.averageFavorableMovePercent,

            averageAdverseMovePercent:
              metric.averageAdverseMovePercent,

            baseWeight:
              metric.baseWeight,

            suggestedWeight:
              metric.suggestedWeight,

            confidence:
              metric.confidence,

            enoughData:
              metric.enoughData,

            delta,

            direction:
              !metric.enoughData
                ? "insufficient"
                : delta > 0.001
                  ? "up"
                  : delta < -0.001
                    ? "down"
                    : "flat",

            winRateLabel:
              finite(metric.winRate)
                ? `${round(
                    metric.winRate,
                    1,
                  )}%`
                : "--",

            averageReturnLabel:
              percent(
                metric.averageReturnPercent,
              ),

            baseWeightLabel:
              weight(
                metric.baseWeight,
              ),

            suggestedWeightLabel:
              weight(
                metric.suggestedWeight,
              ),

            sampleLabel:
              `${metric.sampleSize}件`,
          };
        },
      )
      .sort(
        (first, second) => {
          if (
            first.enoughData !==
            second.enoughData
          ) {
            return first.enoughData
              ? -1
              : 1;
          }

          return (
            Math.abs(
              second.delta || 0,
            ) -
            Math.abs(
              first.delta || 0,
            )
          );
        },
      );

  return {
    version:
      "trade-memory-learning-ui-v1",

    resolvedApprovalCount:
      learning.resolvedApprovalCount,

    eligibleSignalCount:
      learning.eligibleSignalCount,

    totalSignalCount:
      rows.length,

    readyForOptimization:
      learning.readyForOptimization,

    minimumSampleSize:
      learning.minimumSampleSize,

    maximumWeightChangePercent:
      learning.maximumWeightChangePercent,

    rows,

    warnings:
      learning.warnings || [],
  };
}

export function renderTradeMemoryLearningPanel({
  records,
  baseWeights = {},
  documentRef =
    globalThis.document,
}) {
  if (!documentRef) {
    return null;
  }

  const viewModel =
    createTradeMemoryLearningViewModel(
      records,
      baseWeights,
    );

  const section =
    documentRef.createElement(
      "section",
    );

  section.className =
    "tradeMemoryLearningPanel";

  const statusClass =
    viewModel.readyForOptimization
      ? "ready"
      : "waiting";

  const statusLabel =
    viewModel.readyForOptimization
      ? "学習候補あり"
      : "データ蓄積中";

  const rowsHtml =
    viewModel.rows
      .map(
        (row) => `
          <div class="tradeLearningRow ${row.direction}">
            <div class="tradeLearningName">
              <strong>
                ${row.label}
              </strong>

              <span>
                ${row.sampleLabel}
              </span>
            </div>

            <div class="tradeLearningMetric">
              <span>勝率</span>
              <strong>
                ${row.winRateLabel}
              </strong>
            </div>

            <div class="tradeLearningMetric">
              <span>平均損益</span>
              <strong>
                ${row.averageReturnLabel}
              </strong>
            </div>

            <div class="tradeLearningWeight">
              <span>
                ${row.baseWeightLabel}
              </span>

              <b>→</b>

              <strong>
                ${row.suggestedWeightLabel}
              </strong>
            </div>

            <div class="tradeLearningState">
              ${
                row.enoughData
                  ? row.direction === "up"
                    ? "引き上げ候補"
                    : row.direction === "down"
                      ? "引き下げ候補"
                      : "維持候補"
                  : `最低${viewModel.minimumSampleSize}件必要`
              }
            </div>
          </div>
        `,
      )
      .join("");

  const warningHtml =
    viewModel.warnings
      .map(
        (warning) =>
          `<li>${warning}</li>`,
      )
      .join("");

  section.innerHTML = `
    <div class="tradeLearningHeader">
      <div>
        <span class="tradeLearningEyebrow">
          TRADE MEMORY LEARNING
        </span>

        <h3>
          学習ウェイト候補
        </h3>

        <p>
          解決済みのPaper取引結果から、
          指標別の成績を集計しています。
        </p>
      </div>

      <span class="tradeLearningStatus ${statusClass}">
        ${statusLabel}
      </span>
    </div>

    <div class="tradeLearningSummary">
      <div>
        <span>解決済み承認</span>

        <strong>
          ${viewModel.resolvedApprovalCount}
        </strong>
      </div>

      <div>
        <span>学習可能指標</span>

        <strong>
          ${viewModel.eligibleSignalCount}
          /
          ${viewModel.totalSignalCount}
        </strong>
      </div>

      <div>
        <span>変更上限</span>

        <strong>
          ±${viewModel.maximumWeightChangePercent}%
        </strong>
      </div>
    </div>

    <div class="tradeLearningRows">
      ${rowsHtml}
    </div>

    ${
      warningHtml
        ? `
          <ul class="tradeLearningWarnings">
            ${warningHtml}
          </ul>
        `
        : ""
    }

    <p class="tradeLearningDisclaimer">
      推奨ウェイトは自動適用されません。
      バックテストと明示承認後にのみ反映します。
    </p>
  `;

  return section;
}