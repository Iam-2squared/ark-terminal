import {
buildIntegratedAiDecision
} from "./integrated-ai-decision.js";

import {
buildExplainabilityReport,
buildDecisionNarrative
} from "./explainability-engine.js";

export function buildAnalysisCore({

state={},
macroInput={},
marketInput={},
portfolioPlan={}

}={}){

const decision=

buildIntegratedAiDecision({

state,
macroInput,
marketInput,
portfolioPlan

});

const explain=

buildExplainabilityReport({

recommendation:
decision.recommendation,

technicalScore:
decision.technicalScore,

macroScore:
decision.macro.score,

aiScore:
decision.aiScore,

riskScore:
decision.riskScore,

confidence:
decision.confidence

});

const narrative=

buildDecisionNarrative({

report:
explain

});

return{

version:
"analysis-core-v1",

generatedAt:
new Date().toISOString(),

decision,

explainability:
explain,

narrative,

dashboard:{

action:
decision.recommendation.action,

stars:
decision.recommendation.stars,

score:
decision.recommendation.score,

confidence:
decision.confidence,

macro:
decision.macro.sentiment,

regime:
decision.regime.regime

}

};

}

export function buildAnalysisSummary({

analysis

}){

return{

title:
"AI Analysis",

action:
analysis.dashboard.action,

score:
analysis.dashboard.score,

confidence:
analysis.dashboard.confidence,

headline:
analysis.narrative.headline,

summary:
analysis.narrative.summary

};

}
