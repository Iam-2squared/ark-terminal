function clamp(v,min=0,max=100){
    return Math.min(max,Math.max(min,Number(v)||0));
}

export function calibrateConfidence({

score=50,

agreementRate=50,

engineCount=1,

historicalAccuracy=50,

volatility=50

}={}){

const confidence=

score*0.30+

agreementRate*0.25+

historicalAccuracy*0.25+

Math.min(engineCount*10,100)*0.10+

(100-volatility)*0.10;

return{

confidence:

Math.round(

clamp(confidence)

),

level:

confidence>=85

?"Very High"

:confidence>=70

?"High"

:confidence>=55

?"Medium"

:confidence>=40

?"Low"

:"Very Low"

};

}

export class ConfidenceCalibrator{

evaluate(input){

return calibrateConfidence(input);

}

}

export const

confidenceCalibrator=

new ConfidenceCalibrator();