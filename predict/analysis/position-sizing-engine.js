function number(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed)
    ? parsed
    : fallback;
}

function clamp(value, minimum = 0, maximum = 1) {
  return Math.min(
    maximum,
    Math.max(
      minimum,
      number(value)
    )
  );
}

function round(value, digits = 2) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

export function calculatePositionSize({

capital = 0,

allocation = 0,

confidence = 50,

riskLevel = 50,

price = 1

} = {}) {

  const allocationRate =
    clamp(allocation);

  const confidenceRate =
    clamp(confidence / 100);

  const riskRate =
    clamp((100 - riskLevel) / 100);

  const investAmount =
    capital *
    allocationRate *
    confidenceRate *
    riskRate;

  const shares =
    Math.floor(
      investAmount /
      Math.max(1, price)
    );

  return {

    capital:
      round(capital),

    allocation:
      round(allocationRate,4),

    investAmount:
      round(investAmount),

    shares,

    estimatedCost:
      round(shares * price)

  };

}

export class PositionSizingEngine{

calculate(input={}){

return calculatePositionSize(input);

}

}

export const
positionSizingEngine =
new PositionSizingEngine();