function score(v){
    const n=Number(v);
    return Number.isFinite(n)?n:0;
}

function impactLabel(v){

    if(v>=80) return "Very High";
    if(v>=60) return "High";
    if(v>=40) return "Medium";
    if(v>=20) return "Low";

    return "Very Low";
}

export function buildExplainabilityReport({

recommendation={},
technicalScore=50,
macroScore=50,
aiScore=50,
riskScore=50,
confidence=70

}={}){

const factors=[

{
name:"Technical",
score:score(technicalScore),
weight:0.35
},

{
name:"Macro",
score:score(macroScore),
weight:0.20
},

{
name:"AI",
score:score(aiScore),
weight:0.30
},

{
name:"Risk",
score:score(riskScore),
weight:0.15
}

].map(f=>({

...f,

impact:
Math.round(
f.score*f.weight
),

level:
impactLabel(
f.score
)

}));

return{

action:
recommendation.action ??
"HOLD",

confidence,

factors,

topFactors:

[...factors]

.sort(

(a,b)=>

b.impact-a.impact

)

.slice(0,3)

};

}

export function buildDecisionNarrative({

report

}){

const top=

report.topFactors

.map(

x=>x.name

)

.join(", ");

return{

headline:

report.action,

summary:

"Main drivers: "+top,

confidence:

report.confidence

};

}
