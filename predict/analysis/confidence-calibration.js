function num(v,d=0){
    const n=Number(v);
    return Number.isFinite(n)?n:d;
}

function clamp(v,min,max){
    return Math.min(max,Math.max(min,v));
}

function round(v,d=2){
    const f=10**d;
    return Math.round(v*f)/f;
}

export function calibrateConfidence({

confidence=50,
performance={},
sampleSize=0

}={}){

const base=
num(confidence,50);

const accuracy=
num(performance.accuracy,50);

const samples=
Math.max(
0,
num(sampleSize)
);

const reliability=

Math.min(
1,
samples/100
);

const adjusted=

base*0.55+
accuracy*0.45;

const calibrated=

clamp(

adjusted*
(0.6+0.4*reliability),

0,

100

);

return{

rawConfidence:
base,

accuracy,

sampleSize:
samples,

reliability:
round(reliability,3),

confidence:
round(calibrated)

};

}

export function buildConfidenceLabel({

confidence=50

}={}){

if(confidence>=90)
return"Very High";

if(confidence>=75)
return"High";

if(confidence>=60)
return"Moderate";

if(confidence>=40)
return"Low";

return"Very Low";

}

export function buildConfidenceReport({

confidence=50,
performance={},
sampleSize=0

}={}){

const c=

calibrateConfidence({

confidence,
performance,
sampleSize

});

return{

version:

"confidence-calibration-v1",

...c,

label:

buildConfidenceLabel({

confidence:
c.confidence

})

};

}
