import AccuracyDashboardHistory
from "./accuracy-dashboard-history.js";

export function createAccuracyDashboardHistoryManager({

history=
new AccuracyDashboardHistory(),

}={}){

return{

save(snapshot){

history.push(snapshot);

},

latest(){

return history.latest();

},

list(){

return history.all();

},

clear(){

history.clear();

},

};

}

export default createAccuracyDashboardHistoryManager;
