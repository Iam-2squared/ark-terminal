function number(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed)
    ? parsed
    : fallback;
}

function clamp(value, min = 0, max = 100) {
  return Math.min(
    max,
    Math.max(
      min,
      number(value)
    )
  );
}

function normalizeWeight(value) {
  return Math.max(
    0,
    number(value, 1)
  );
}

function scoreToAction(score) {

  if (score >= 85) {
    return "STRONG BUY";
  }

  if (score >= 70) {
    return "BUY";
  }

  if (score >= 55) {
    return "WATCH";
  }

  if (score >= 40) {
    return "HOLD";
  }

  if (score >= 20) {
    return "REDUCE";
  }

  return "SELL";
}

export function fuseEngineDecisions({

engines=[]

}={}){

if(engines.length===0){

return{

score:50,

confidence:0,

action:"HOLD",

engineCount:0

};

}

let totalWeight=0;
let score=0;
let confidence=0;

for(const engine of engines){

const weight=

normalizeWeight(

engine.weight

);

totalWeight+=weight;

score+=

clamp(

engine.score

)*weight;

confidence+=

clamp(

engine.confidence,

0,

100

)*weight;

}

score/=totalWeight;
confidence/=totalWeight;

return{

score:

Math.round(

score*100

)/100,

confidence:

Math.round(

confidence*100

)/100,

action:

scoreToAction(

score

),

engineCount:

engines.length

};

}

export class DecisionFusionEngine{

run(input){

return fuseEngineDecisions(input);

}

}

export const

decisionFusionEngine=

new DecisionFusionEngine();