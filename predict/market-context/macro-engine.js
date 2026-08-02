function n(v,d=0){
    const x=Number(v);
    return Number.isFinite(x)?x:d;
}

export function evaluateMacroEnvironment({

nikkei=0,
nasdaq=0,
sox=0,
usdjpy=150,
vix=20,
bondYield=4.0,
oil=80

}={}){

nikkei=n(nikkei);
nasdaq=n(nasdaq);
sox=n(sox);
usdjpy=n(usdjpy);
vix=n(vix);
bondYield=n(bondYield);
oil=n(oil);

let score=50;

if(nikkei>0)score+=10;
else score-=10;

if(nasdaq>0)score+=15;
else score-=15;

if(sox>0)score+=15;
else score-=15;

if(vix<20)score+=10;
else if(vix>30)score-=15;

if(bondYield<4.5)score+=5;
else score-=5;

if(oil<90)score+=5;
else score-=5;

score=Math.max(
0,
Math.min(
100,
score
)
);

let sentiment="NEUTRAL";

if(score>=70)
sentiment="BULLISH";

else if(score<=35)
sentiment="BEARISH";

return{

score,
sentiment,

markets:{
nikkei,
nasdaq,
sox,
usdjpy,
vix,
bondYield,
oil
}

};

}

export function buildMacroSummary({

macro

}){

return{

title:
"Macro Environment",

score:
macro.score,

sentiment:
macro.sentiment

};

}
