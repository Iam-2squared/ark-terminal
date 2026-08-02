import createAccuracyDashboardPanel
from "./accuracy-dashboard-panel.js";

export function buildAccuracyDashboardPage(vm){
    return{
        panel:createAccuracyDashboardPanel(vm),
        generatedAt:new Date().toISOString(),
    };
}

export default buildAccuracyDashboardPage;
