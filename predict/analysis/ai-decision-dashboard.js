
import {
  createAiAnalysis,
} from "./ai-analysis.js";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(
      Number(value),
    )
  );
}

function clamp(
  value,
  minimum = 0,
  maximum = 100,
) {
  return Math.min(
    maximum,
    Math.max(
      minimum,
      Number(value) || 0,
    ),
  );
}

function round(
  value,
  digits = 1,
) {
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

function formatPrice(value) {
  if (!finite(value)) {
    return "--";
  }

  const number =
    Number(value);

  return (
    "¥" +
    number.toLocaleString(
      "ja-JP",
      {
        minimumFractionDigits:
          number < 100 ? 1 : 0,

        maximumFractionDigits:
          number < 100 ? 1 : 0,
      },
    )
  );
}

function scoreStatus(score) {
  if (score >= 70) {
    return "positive";
  }

  if (score >= 45) {
    return "neutral";
  }

  return "negative";
}

function movingAverageScore(
  indicators,
) {
  const movingAverages =
    indicators.movingAverages || {};

  let score = 50;

  if (
    finite(
      indicators.currentPrice,
    ) &&
    finite(
      movingAverages.ma25,
    )
  ) {
    score +=
      indicators.currentPrice >=
      movingAverages.ma25
        ? 14
        : -14;
  }

  if (
    finite(movingAverages.ma5) &&
    finite(movingAverages.ma25)
  ) {
    score +=
      movingAverages.ma5 >=
      movingAverages.ma25
        ? 12
        : -12;
  }

  if (
    finite(movingAverages.ma25) &&
    finite(movingAverages.ma75)
  ) {
    score +=
      movingAverages.ma25 >=
      movingAverages.ma75
        ? 12
        : -12;
  }

  if (
    finite(movingAverages.ma75) &&
    finite(movingAverages.ma200)
  ) {
    score +=
      movingAverages.ma75 >=
      movingAverages.ma200
        ? 10
        : -10;
  }

  return clamp(score);
}

function rsiScore(value) {
  if (!finite(value)) {
    return 50;
  }

  const rsi =
    Number(value);

  if (
    rsi >= 45 &&
    rsi <= 60
  ) {
    return 84;
  }

  if (
    rsi > 60 &&
    rsi < 70
  ) {
    return 72;
  }

  if (
    rsi >= 35 &&
    rsi < 45
  ) {
    return 67;
  }

  if (
    rsi >= 25 &&
    rsi < 35
  ) {
    return 56;
  }

  if (
    rsi >= 70 &&
    rsi < 80
  ) {
    return 38;
  }

  return rsi < 25
    ? 35
    : 20;
}

function macdScore(
  indicators,
) {
  const macd =
    indicators.macd || {};

  if (
    finite(macd.value) &&
    finite(macd.signal)
  ) {
    const crossedUp =
      finite(macd.previousValue) &&
      finite(macd.previousSignal) &&
      macd.previousValue <=
        macd.previousSignal &&
      macd.value >
        macd.signal;

    const crossedDown =
      finite(macd.previousValue) &&
      finite(macd.previousSignal) &&
      macd.previousValue >=
        macd.previousSignal &&
      macd.value <
        macd.signal;

    if (crossedUp) {
      return 90;
    }

    if (crossedDown) {
      return 22;
    }

    return macd.value >=
      macd.signal
      ? 68
      : 35;
  }

  if (
    finite(macd.histogram)
  ) {
    return macd.histogram > 0
      ? 70
      : 32;
  }

  return 50;
}

function volumeScore(
  indicators,
) {
  const ratio =
    indicators.volume?.ratio;

  if (!finite(ratio)) {
    return 50;
  }

  if (ratio >= 2) {
    return 92;
  }

  if (ratio >= 1.2) {
    return 80;
  }

  if (ratio >= 1) {
    return 65;
  }

  if (ratio >= 0.7) {
    return 44;
  }

  return 24;
}

function vwapScore(
  indicators,
) {
  if (
    !finite(
      indicators.currentPrice,
    ) ||
    !finite(
      indicators.vwap,
    )
  ) {
    return 50;
  }

  const distance =
    (
      (
        indicators.currentPrice -
        indicators.vwap
      ) /
      indicators.vwap
    ) * 100;

  if (
    distance >= 0 &&
    distance <= 3
  ) {
    return 84;
  }

  if (
    distance > 3 &&
    distance <= 7
  ) {
    return 70;
  }

  if (
    distance < 0 &&
    distance >= -2
  ) {
    return 54;
  }

  return distance > 7
    ? 48
    : 28;
}

function adxScore(
  indicators,
) {
  const value =
    indicators.adx?.value;

  if (!finite(value)) {
    return 50;
  }

  if (value >= 35) {
    return 90;
  }

  if (value >= 25) {
    return 76;
  }

  if (value >= 18) {
    return 55;
  }

  return 34;
}

function atrScore(
  indicators,
) {
  const percent =
    indicators.atr?.percent;

  if (!finite(percent)) {
    return 50;
  }

  if (
    percent >= 1.2 &&
    percent <= 3.5
  ) {
    return 78;
  }

  if (percent < 1.2) {
    return 58;
  }

  if (percent <= 5) {
    return 51;
  }

  if (percent <= 8) {
    return 34;
  }

  return 18;
}

function bollingerScore(
  indicators,
) {
  const percentB =
    indicators
      .bollingerBands
      ?.percentB;

  if (!finite(percentB)) {
    return 50;
  }

  if (
    percentB >= 0.35 &&
    percentB <= 0.75
  ) {
    return 76;
  }

  if (
    percentB > 0.75 &&
    percentB <= 0.9
  ) {
    return 64;
  }

  if (
    percentB >= 0.15 &&
    percentB < 0.35
  ) {
    return 62;
  }

  return percentB > 0.9
    ? 36
    : 48;
}

function stochasticScore(
  indicators,
) {
  const stochastic =
    indicators.stochastic || {};

  const k =
    stochastic.k ??
    stochastic.value;

  const d =
    stochastic.d ??
    stochastic.signal;

  if (!finite(k)) {
    return 50;
  }

  if (
    finite(d) &&
    k > d &&
    k < 80
  ) {
    return 80;
  }

  if (
    k >= 20 &&
    k <= 70
  ) {
    return 68;
  }

  return k >= 80
    ? 34
    : 48;
}

function buildIndicatorScores(
  state,
) {
  const indicators =
    state.indicators || {};

  const values = [
    [
      "movingAverages",
      "移動平均",
      movingAverageScore(
        indicators,
      ),
      "株価と5・25・75・200日線の位置関係",
    ],

    [
      "rsi",
      "RSI",
      rsiScore(
        indicators.rsi,
      ),
      finite(
        indicators.rsi,
      )
        ? `RSI ${round(
            indicators.rsi,
            1,
          )}`
        : "RSIデータ不足",
    ],

    [
      "macd",
      "MACD",
      macdScore(
        indicators,
      ),
      "MACDとシグナルの方向",
    ],

    [
      "volume",
      "出来高",
      volumeScore(
        indicators,
      ),
      finite(
        indicators
          .volume
          ?.ratio,
      )
        ? `平均の${round(
            indicators
              .volume
              .ratio,
            2,
          )}倍`
        : "出来高倍率なし",
    ],

    [
      "vwap",
      "VWAP",
      vwapScore(
        indicators,
      ),
      "現在値とVWAPの位置",
    ],

    [
      "adx",
      "ADX",
      adxScore(
        indicators,
      ),
      finite(
        indicators
          .adx
          ?.value,
      )
        ? `ADX ${round(
            indicators
              .adx
              .value,
            1,
          )}`
        : "ADXデータ不足",
    ],

    [
      "atr",
      "ATR",
      atrScore(
        indicators,
      ),
      finite(
        indicators
          .atr
          ?.percent,
      )
        ? `ATR比率 ${round(
            indicators
              .atr
              .percent,
            1,
          )}%`
        : "ATRデータ不足",
    ],

    [
      "bollinger",
      "ボリンジャー",
      bollingerScore(
        indicators,
      ),
      "バンド内の価格位置",
    ],

    [
      "stochastic",
      "ストキャス",
      stochasticScore(
        indicators,
      ),
      "短期過熱と反転の方向",
    ],
  ];

  return values.map(
    ([
      key,
      label,
      score,
      reason,
    ]) => ({
      key,
      label,

      score:
        Math.round(score),

      status:
        scoreStatus(score),

      reason,
    }),
  );
}

function recommendation(
  score,
  confidence,
) {
  if (
    score >= 78 &&
    confidence >= 65
  ) {
    return {
      key: "buy",
      label:
        "買い候補",
      note:
        "押し目・節目確認後",
    };
  }

  if (score >= 65) {
    return {
      key: "watch",
      label:
        "監視優先",
      note:
        "条件成立待ち",
    };
  }

  if (score >= 48) {
    return {
      key: "neutral",
      label:
        "中立",
      note:
        "方向確認待ち",
    };
  }

  return {
    key: "avoid",
    label:
      "見送り",
    note:
      "リスク優先",
  };
}

function deriveTradePlan(
  state,
) {
  const indicators =
    state.indicators || {};

  const current =
    finite(
      indicators.currentPrice,
    )
      ? Number(
          indicators.currentPrice,
        )
      : finite(
          state.quote?.price,
        )
        ? Number(
            state.quote.price,
          )
        : null;

  if (
    !finite(current) ||
    current <= 0
  ) {
    return {
      actionable: false,
      entryLabel: "--",
      stopLossLabel: "--",
      firstTargetLabel: "--",
      secondTargetLabel: "--",
      riskReward: null,
    };
  }

  const atr =
    finite(
      indicators
        .atr
        ?.value,
    )
      ? Number(
          indicators
            .atr
            .value,
        )
      : finite(
          indicators
            .atr
            ?.percent,
        )
        ? (
            current *
            Number(
              indicators
                .atr
                .percent,
            )
          ) / 100
        : current * 0.025;

  const ma25 =
    finite(
      indicators
        .movingAverages
        ?.ma25,
    )
      ? Number(
          indicators
            .movingAverages
            .ma25,
        )
      : current;

  const vwap =
    finite(
      indicators.vwap,
    )
      ? Number(
          indicators.vwap,
        )
      : current;

  const anchor =
    Math.max(
      current * 0.96,

      Math.min(
        current,
        ma25,
        vwap,
      ),
    );

  const entryLow =
    Math.max(
      anchor -
        atr * 0.25,

      current * 0.96,
    );

  const entryHigh =
    Math.min(
      anchor +
        atr * 0.25,

      current * 1.015,
    );

  const center =
    (
      entryLow +
      entryHigh
    ) / 2;

  const stopLoss =
    entryLow -
    atr * 1.25;

  const risk =
    Math.max(
      center -
        stopLoss,

      atr * 0.8,
    );

  const firstTarget =
    center +
    risk * 1.5;

  const secondTarget =
    center +
    risk * 2.4;

  return {
    actionable: true,

    entryLabel:
      `${formatPrice(
        entryLow,
      )} 〜 ${formatPrice(
        entryHigh,
      )}`,

    stopLossLabel:
      formatPrice(
        stopLoss,
      ),

    firstTargetLabel:
      formatPrice(
        firstTarget,
      ),

    secondTargetLabel:
      formatPrice(
        secondTarget,
      ),

    riskReward:
      round(
        (
          secondTarget -
          center
        ) / risk,
        2,
      ),
  };
}

function deriveMarketEnvironment(
  state,
) {
  const market =
    state.marketEnvironment || {};

  const score =
    finite(market.score)
      ? clamp(
          market.score,
        )
      : finite(
          market.totalScore,
        )
        ? clamp(
            market.totalScore,
          )
        : 50;

  return {
    score:
      Math.round(score),

    regime:
      market.regime ||
      market.label ||
      "中立",

    status:
      scoreStatus(score),

    explanation:
      market.explanation ||
      market.summary ||
      "市場データが限定的なため、個別株テクニカルを優先しています。",
  };
}

export function createDecisionDashboard(
  state,
) {
  const base =
    createAiAnalysis(state);

  const indicatorScores =
    buildIndicatorScores(
      state,
    );

  const confidence =
    Number(
      base.confidence
        ?.score || 0,
    );

  const recommendationResult =
    recommendation(
      Number(
        base.overallAiScore ||
        0,
      ),

      confidence,
    );

  const tradePlan =
    deriveTradePlan(
      state,
    );

  const focusFactors =
    [
      ...indicatorScores,
    ]
      .sort(
        (
          first,
          second,
        ) =>
          Math.abs(
            second.score -
            50,
          ) -
          Math.abs(
            first.score -
            50,
          ),
      )
      .slice(0, 3)
      .map(
        (
          item,
          index,
        ) => ({
          rank:
            index + 1,

          label:
            item.label,

          score:
            item.score,

          direction:
            item.score >= 50
              ? "プラス"
              : "警戒",

          reason:
            item.reason,
        }),
      );

  return {
    ...base,

    version:
      "ai-decision-dashboard-v1",

    recommendation:
      recommendationResult,

    indicatorScores,

    tradePlan,

    focusFactors,

    marketEnvironment:
      deriveMarketEnvironment(
        state,
      ),

    overallAssessment:
      `${recommendationResult.label}。AI総合スコアは${base.overallAiScore}点、信頼度は${confidence}点です。`,

    entrySuggestion:
      tradePlan.entryLabel,

    stopLossSuggestion:
      tradePlan.stopLossLabel,

    takeProfitSuggestion:
      tradePlan.actionable
        ? `${tradePlan.firstTargetLabel} / ${tradePlan.secondTargetLabel}`
        : "--",
  };
}
