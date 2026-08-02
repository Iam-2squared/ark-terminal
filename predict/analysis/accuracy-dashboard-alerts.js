export function evaluateAccuracyAlerts(summary = {}) {

const alerts=[];

if((summary.accuracy??1)<0.6){
alerts.push({
level:"warning",
message:"Accuracy dropped below 60%",
});
}

if((summary.profitFactor??2)<1){
alerts.push({
level:"critical",
message:"Profit Factor below 1",
});
}

if((summary.maxDrawdown??0)>0.2){
alerts.push({
level:"warning",
message:"Large drawdown detected",
});
}

return alerts;

}

export default evaluateAccuracyAlerts;
