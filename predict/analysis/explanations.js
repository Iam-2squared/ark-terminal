function number(value, digits = 2) {
  return Number(value).toLocaleString("ja-JP", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
}

export function explainMovingAverages({
  currentPrice,
  ma5,
  ma25,
  ma75,
  ma200,
}) {
  const values = [currentPrice, ma5, ma25, ma75, ma200];

  if (values.some((value) => !Number.isFinite(Number(value)))) {
    return "移動平均線の計算に必要な履歴が不足しています。";
  }

  if (currentPrice > ma5 && ma5 > ma25 && ma25 > ma75 && ma75 > ma200) {
    return "株価・5日線・25日線・75日線・200日線が上向きの順序に並んでいます。";
  }

  if (currentPrice < ma5 && ma5 < ma25 && ma25 < ma75 && ma75 < ma200) {
    return "株価・5日線・25日線・75日線・200日線が下向きの順序に並んでいます。";
  }

  const deviation = ((currentPrice - ma25) / ma25) * 100;

  return (
    `株価は25日線から` +
    `${number(deviation)}%` +
    `${deviation >= 0 ? "上" : "下"}` +
    "にあり、移動平均線の並びは混在しています。"
  );
}

export function explainRsi(rsi) {
  if (rsi >= 70) {
    return `RSIは${number(rsi, 1)}で、買われ過ぎに注意が必要な水準です。`;
  }

  if (rsi <= 30) {
    return `RSIは${number(rsi, 1)}で、売られ過ぎ水準ですが下落継続にも注意が必要です。`;
  }

  return `RSIは${number(rsi, 1)}で、中立圏にあります。`;
}

export function explainMacd(macd) {
  const crossedUp =
    Number.isFinite(macd.previousValue) &&
    Number.isFinite(macd.previousSignal) &&
    macd.previousValue <= macd.previousSignal &&
    macd.value > macd.signal;

  const crossedDown =
    Number.isFinite(macd.previousValue) &&
    Number.isFinite(macd.previousSignal) &&
    macd.previousValue >= macd.previousSignal &&
    macd.value < macd.signal;

  if (crossedUp) {
    return "MACDがシグナルを上抜き、ゴールデンクロスが発生しました。";
  }

  if (crossedDown) {
    return "MACDがシグナルを下抜き、デッドクロスが発生しました。";
  }

  return (
    `MACDヒストグラムは` +
    `${number(macd.histogram)}で、` +
    `${
      macd.histogram >= 0
        ? "上向きの勢いが優勢です。"
        : "下向きの勢いが優勢です。"
    }`
  );
}

export function explainBollinger(bands) {
  if (bands.percentB > 1) {
    return "株価はボリンジャーバンド上限を上回り、上昇の強さと短期的な過熱が同時に見られます。";
  }

  if (bands.percentB < 0) {
    return "株価はボリンジャーバンド下限を下回り、売られ過ぎと下落継続の両方に注意が必要です。";
  }

  return (
    `株価はバンド内の` + `${number(bands.percentB * 100, 0)}%位置にあります。`
  );
}

export function explainVolume(volume, priceChangePercent) {
  return (
    `出来高は20日平均の` +
    `${number(volume.ratio, 2)}倍で、` +
    `株価は前日比` +
    `${number(priceChangePercent, 2)}%です。`
  );
}

export function explainAdx(adx) {
  const direction = adx.plusDi >= adx.minusDi ? "上向き" : "下向き";

  return (
    `ADXは${number(adx.value, 1)}で、` +
    `${
      adx.value >= 25
        ? `${direction}トレンドに強さがあります。`
        : "明確なトレンドはまだ弱い状態です。"
    }`
  );
}

export function explainAtr(atr) {
  return (
    `ATRは株価の${number(atr.percent, 2)}%で、` +
    `${
      atr.percent >= 5
        ? "値動きが大きくリスク管理が重要です。"
        : "値動きは比較的安定しています。"
    }`
  );
}

export function explainStochastic(stochastic) {
  if (stochastic.k >= 80) {
    return `ストキャスティクス%Kは${number(stochastic.k, 1)}で、買われ過ぎ圏です。`;
  }

  if (stochastic.k <= 20) {
    return `ストキャスティクス%Kは${number(stochastic.k, 1)}で、売られ過ぎ圏です。`;
  }

  return (
    `ストキャスティクスは%K ` +
    `${number(stochastic.k, 1)}、` +
    `%D ${number(stochastic.d, 1)}です。`
  );
}

export function explainVwap(currentPrice, vwap) {
  const difference = ((currentPrice - vwap) / vwap) * 100;

  return (
    `株価は20日VWAPより` +
    `${number(Math.abs(difference), 2)}%` +
    `${difference >= 0 ? "上" : "下"}` +
    "にあります。"
  );
}

export function explain52WeekHigh(distance) {
  return `52週高値まで` + `${number(Math.abs(distance), 2)}%です。`;
}

export function explain52WeekLow(distance) {
  return `52週安値から` + `${number(distance, 2)}%上にあります。`;
}
