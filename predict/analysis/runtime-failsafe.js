import {
buildValidationReport
} from "./data-validation-engine.js";

export function runFailSafe(input={}){

const report=

buildValidationReport(input);

if(report.valid){

return{

allow:true,

validation:report,

html:""

};

}

const errorList=

report.errors

.map(

x=>`<li>${x}</li>`

)

.join("");

const warningList=

report.warnings

.map(

x=>`<li>${x}</li>`

)

.join("");

return{

allow:false,

validation:report,

html:`

<section class="arkFailSafe">

<h2>

AI Analysis Stopped

</h2>

<p>

Input validation failed.

</p>

<h3>

Errors

</h3>

<ul>

${errorList}

</ul>

<h3>

Warnings

</h3>

<ul>

${warningList}

</ul>

<div>

Health

${report.health}

</div>

</section>

`

};

}

export function shouldRunAnalysis(input = {}) {
  return runFailSafe(input).allow;
}