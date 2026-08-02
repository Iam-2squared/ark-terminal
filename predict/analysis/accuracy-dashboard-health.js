import evaluateAccuracyAlerts
from "./accuracy-dashboard-alerts.js";

export function createAccuracyDashboardHealth(summary={}){

const alerts=
evaluateAccuracyAlerts(summary);

return{

status:
alerts.some(x=>x.level==="critical")
?"critical"
:alerts.length
?"warning"
:"healthy",

alerts,

};

}

export default createAccuracyDashboardHealth;
