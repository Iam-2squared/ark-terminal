import {
analysisCache
} from "./analysis-cache.js";

import {
analysisJobQueue
} from "./analysis-job-queue.js";

import {
performanceMonitor
} from "./performance-monitor.js";

export class RuntimeV2 {

constructor(){

this.version=
"2.0.0";

}

async execute(

key,

worker

){

const cached=

analysisCache.get?.(
key
);

if(cached){

return cached;

}

return analysisJobQueue.add(
async()=>{

const timer=
performanceMonitor.start(key);

const result=
await worker();

performanceMonitor.end(
timer
);

analysisCache.set?.(
key,
result
);

return result;

}
);

}

stats(){

return{

version:
this.version,

cache:
analysisCache.size?.() ?? 0,

queue:
analysisJobQueue.stats(),

performance:
performanceMonitor.summary()

};

}

}

export const
runtimeV2=
new RuntimeV2();