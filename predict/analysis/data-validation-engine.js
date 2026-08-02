function finite(value){
    return Number.isFinite(Number(value));
}

function clamp(value,min,max){
    return Math.min(max,Math.max(min,Number(value)||0));
}

export function validateAnalysisInput({

state={},
macroInput={},
marketInput={}

}={}){

const errors=[];
const warnings=[];

const tech=
state.analysis?.technicalScore;

if(!finite(tech))
errors.push("technicalScore");

const confidence=
state.prediction?.confidence;

if(!finite(confidence))
warnings.push("confidence");

const rsi=
state.indicators?.rsi;

if(
finite(rsi)&&
(Number(rsi)<0||Number(rsi)>100)
){
errors.push("rsi");
}

const adx=
state.indicators?.adx?.value ??
state.indicators?.adx;

if(
finite(adx)&&
Number(adx)<0
){
errors.push("adx");
}

const vix=
macroInput.vix;

if(
finite(vix)&&
Number(vix)<0
){
errors.push("vix");
}

const trend=
marketInput.trendScore;

if(
finite(trend)&&
(Number(trend)<0||Number(trend)>100)
){
errors.push("trendScore");
}

return{

valid:
errors.length===0,

errors,

warnings

};

}

export function buildValidationReport(input={}){

const validation=
validateAnalysisInput(input);

const health=

validation.valid
?100
:clamp(
100-
validation.errors.length*25-
validation.warnings.length*5,
0,
100
);

return{

version:
"validation-engine-v1",

...validation,

health

};

}