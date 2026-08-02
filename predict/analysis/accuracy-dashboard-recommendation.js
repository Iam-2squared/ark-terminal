export function createAccuracyRecommendation(report={}){

const accuracy=report.overview?.accuracy??0;
const pf=report.overview?.profitFactor??0;
const sharpe=report.overview?.sharpe??0;

let rating="C";
let action="Monitor";

if(accuracy>=0.8&&pf>=1.5&&sharpe>=1){
rating="A";
action="Deploy";
}
else if(accuracy>=0.7&&pf>=1.2){
rating="B";
action="Observe";
}

return{

rating,

action,

score:
Math.round(
accuracy*100+
pf*20+
sharpe*10
),

};

}

export default createAccuracyRecommendation;
