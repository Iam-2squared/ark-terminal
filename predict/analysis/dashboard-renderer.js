export function renderAiDashboard({

analysis

}){

const d=analysis.dashboard;

return `

<section class="ai-dashboard">

<div class="ai-title">

AI Analysis

</div>

<div class="ai-action">

${d.action}

</div>

<div class="ai-stars">

${"★".repeat(d.stars)}

</div>

<div class="ai-score">

Score ${d.score}

</div>

<div class="ai-confidence">

Confidence ${d.confidence}%

</div>

<div class="ai-market">

${d.macro}

/

${d.regime}

</div>

</section>

`;

}

export function renderReasonList(list=[]){

return`

<ul>

${list.map(

x=>`<li>${x}</li>`

).join("")}

</ul>

`;

}
