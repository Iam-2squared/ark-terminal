import {
runtimeV2
}
from "./runtime-v2.js";

export class AnalysisOrchestrator{

async analyze({

symbol,

engines=[]

}){

const results=[];

for(const engine of engines){

const value=

await runtimeV2.execute(

symbol+"-"+engine.name,

()=>engine.run(symbol)

);

results.push({

name:engine.name,

result:value

});

}

return{

symbol,

engines:results,

generatedAt:
Date.now()

};

}

}

export const
analysisOrchestrator=
new AnalysisOrchestrator();