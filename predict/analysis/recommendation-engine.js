function n(v,d=0){
    const x=Number(v);
    return Number.isFinite(x)?x:d;
}

function clamp(v,min,max){
    return Math.min(max,Math.max(min,v));
}

export function buildRecommendation({

technicalScore=50,
macroScore=50,
aiScore=50,
riskScore=50,
confidence=70

}={}){

technicalScore=n(technicalScore);
macroScore=n(macroScore);
aiScore=n(aiScore);
riskScore=n(riskScore);
confidence=n(confidence);

const total=

technicalScore*0.35+
macroScore*0.20+
aiScore*0.30+
riskScore*0.15;

const score=
Math.round(
clamp(total,0,100)
);

let action="HOLD";
let stars=3;

if(score>=85){

action="STRONG BUY";
stars=5;

}

else if(score>=70){

action="BUY";
stars=4;

}

else if(score>=55){

action="WATCH";
stars=3;

}

else if(score>=40){

action="REDUCE";
stars=2;

}

else{

action="SELL";
stars=1;

}

const expectedReturn=

Math.round(
(score-50)*0.6
);

const expectedRisk=

Math.round(
(100-score)*0.25
);

return{

action,
stars,
score,
confidence,

expectedReturn,

expectedRisk,

summary:{

technicalScore,
macroScore,
aiScore,
riskScore

}

};

}

export function recommendationBadge({

recommendation

}){

return{

label:
recommendation.action,

stars:
recommendation.stars,

confidence:
recommendation.confidence

};

}
