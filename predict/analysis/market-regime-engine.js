function number(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed)
    ? parsed
    : fallback;
}

function clamp(value, min = 0, max = 100) {
  return Math.min(max, Math.max(min, number(value)));
}

export function detectMarketRegime({

trendScore = 50,

volatility = 20,

breadth = 50,

momentum = 50,

vix = 20

} = {}) {

  trendScore = clamp(trendScore);
  breadth = clamp(breadth);
  momentum = clamp(momentum);
  volatility = clamp(volatility);
  vix = Math.max(0, number(vix));

  let regime = "SIDEWAYS";

  if (
    trendScore >= 70 &&
    momentum >= 65 &&
    breadth >= 60 &&
    vix < 25
  ) {
    regime = "BULL";
  }
  else if (
    trendScore <= 35 &&
    momentum <= 40 &&
    breadth <= 45
  ) {
    regime = "BEAR";
  }
  else if (
    volatility >= 70 ||
    vix >= 35
  ) {
    regime = "HIGH_VOLATILITY";
  }

  let riskMultiplier = 1.0;

  switch(regime){

    case "BULL":
      riskMultiplier = 1.20;
      break;

    case "SIDEWAYS":
      riskMultiplier = 0.90;
      break;

    case "HIGH_VOLATILITY":
      riskMultiplier = 0.65;
      break;

    case "BEAR":
      riskMultiplier = 0.45;
      break;

  }

  return{

    regime,

    riskMultiplier,

    score:

    Math.round(

      trendScore*0.4+

      momentum*0.3+

      breadth*0.3

    )

  };

}

export class MarketRegimeEngine{

analyze(input={}){

return detectMarketRegime(input);

}

}

export const
marketRegimeEngine=
new MarketRegimeEngine();