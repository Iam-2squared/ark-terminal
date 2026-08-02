function number(value,fallback=0){
    const n=Number(value);
    return Number.isFinite(n)?n:fallback;
}

function round(value,digits=2){
    const f=10**digits;
    return Math.round(value*f)/f;
}

function scoreModel(model){

    const accuracy=
    number(model.accuracy);

    const profitFactor=
    number(model.profitFactor);

    const drawdown=
    number(model.maxDrawdown);

    const latency=
    number(model.latency);

    return round(

        accuracy*0.45+

        Math.min(profitFactor,5)*12-

        drawdown*0.25-

        latency*0.05

    );

}

export function benchmarkModels({

models=[]

}={}){

const ranked=

models

.map(model=>({

...model,

benchmarkScore:

scoreModel(model)

}))

.sort(

(a,b)=>

b.benchmarkScore-

a.benchmarkScore

);

return{

best:

ranked[0]??null,

ranking:

ranked,

count:

ranked.length

};

}

export class ModelBenchmarkEngine{

evaluate(input){

return benchmarkModels(input);

}

}

export const

modelBenchmarkEngine=

new ModelBenchmarkEngine();