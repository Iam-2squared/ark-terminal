export function createAccuracyDashboardSnapshot(vm={}){

return{

createdAt:new Date().toISOString(),

cards:structuredClone(vm.cards??[]),

health:structuredClone(vm.health??{}),

metadata:structuredClone(vm.metadata??{}),

};

}

export default createAccuracyDashboardSnapshot;
