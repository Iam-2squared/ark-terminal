import generateAccuracyDashboardReport
from "./accuracy-dashboard-report.js";

export function scoreAccuracyDashboard(report={}){

const a=report.overview?.accuracy??0;
const p=report.overview?.profitFactor??0;
const s=report.overview?.sharpe??0;

return Math.round(
(a*50)+(Math.min(p,3)/3*30)+(Math.min(s,3)/3*20)
);

}

export default scoreAccuracyDashboard;
