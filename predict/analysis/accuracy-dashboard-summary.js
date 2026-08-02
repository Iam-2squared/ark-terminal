import calculateAccuracyTrend
from "./accuracy-dashboard-trend.js";

export function summarizeAccuracyDashboard(history=[]){

return{

trend:
calculateAccuracyTrend(history),

latest:
history[0]??null,

count:
history.length,

};

}

export default summarizeAccuracyDashboard;
