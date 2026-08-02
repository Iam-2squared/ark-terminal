import{
buildAnalysisCore
}from "./analysis-core.js";

import{
renderAiDashboard,
renderReasonList
}from "./dashboard-renderer.js";

export function renderAnalysisPanel({

state={},
macroInput={},
marketInput={},
portfolioPlan={}

}={}){

const analysis=

buildAnalysisCore({

state,
macroInput,
marketInput,
portfolioPlan

});

return`

<div class="ark-ai-panel">

${renderAiDashboard({

analysis

})}

<h3>

Buy Factors

</h3>

${renderReasonList(

analysis.decision.buyFactors

)}

<h3>

Risk Factors

</h3>

${renderReasonList(

analysis.decision.riskFactors

)}

<div class="ai-summary">

${analysis.narrative.summary}

</div>

</div>

`;

}

export function createAnalysisView(input){

return{

html:

renderAnalysisPanel(input),

createdAt:

new Date().toISOString()

};

}
