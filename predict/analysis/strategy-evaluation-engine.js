function number(value,fallback=0){
  const n=Number(value);
  return Number.isFinite(n)?n:fallback;
}

function round(value,digits=2){
  const factor=10**digits;
  return Math.round(value*factor)/factor;
}

function clamp(value,min=0,max=100){
  return Math.min(max,Math.max(min,number(value)));
}

export function evaluateStrategy({

history=[]

}={}){

const trades=

Array.isArray(history)
?history
:[];

if(trades.length===0){

return{

trades:0,
winRate:0,
averageReturn:0,
profitFactor:0,
maxDrawdown:0,
score:0

};

}

let wins=0;
let profit=0;
let loss=0;
let equity=0;
let peak=0;
let maxDrawdown=0;

for(const trade of trades){

const result=

number(
trade.return
);

equity+=result;

peak=

Math.max(
peak,
equity
);

maxDrawdown=

Math.max(
maxDrawdown,
peak-equity
);

if(result>0){

wins++;
profit+=result;

}else{

loss+=Math.abs(result);

}

}

const winRate=

wins/
trades.length*
100;

const averageReturn=

trades.reduce(
(a,b)=>a+
number(b.return),
0
)
/trades.length;

const profitFactor=

loss===0
?profit
:profit/loss;

const score=

clamp(

winRate*0.35+

Math.min(
profitFactor,
5
)*15+

Math.max(
averageReturn,
0
)*2-

maxDrawdown*0.2

);

return{

trades:
trades.length,

winRate:
round(winRate),

averageReturn:
round(averageReturn),

profitFactor:
round(profitFactor),

maxDrawdown:
round(maxDrawdown),

score:
round(score)

};

}

export class StrategyEvaluationEngine{

evaluate(input){

return evaluateStrategy(input);

}

}

export const

strategyEvaluationEngine=

new StrategyEvaluationEngine();