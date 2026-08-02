import createAccuracyRecommendation
from "./accuracy-dashboard-recommendation.js";

export function buildAccuracyDashboardDecision(report={}){

const recommendation=
createAccuracyRecommendation(report);

return{

approved:
recommendation.rating==="A",

recommendation,

};

}

export default buildAccuracyDashboardDecision;
