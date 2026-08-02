function num(v,d=0){
    const n=Number(v);
    return Number.isFinite(n)?n:d;
}

function round(v,d=2){
    const f=10**d;
    return Math.round(v*f)/f;
}

export function splitWalkForward({

history=[],
trainRatio=0.7

}={}){

const split=

Math.max(

1,

Math.floor(

history.length*
trainRatio

)

);

return{

train:

history.slice(

0,

split

),

test:

history.slice(

split

)

};

}

export function evaluateWalkForward({

history=[],
trainRatio=0.7

}={}){

const data=

splitWalkForward({

history,
trainRatio

});

const trainAvg=

data.train.reduce(

(a,b)=>a+num(b.return),

0

)/Math.max(

1,

data.train.length

);

const testAvg=

data.test.reduce(

(a,b)=>a+num(b.return),

0

)/Math.max(

1,

data.test.length

);

return{

trainCount:

data.train.length,

testCount:

data.test.length,

trainAverage:

round(trainAvg),

testAverage:

round(testAvg),

stable:

Math.abs(

trainAvg-testAvg

)<5

};

}

export function buildWalkForwardReport({

history=[]

}={}){

const r=

evaluateWalkForward({

history

});

return{

version:

"walk-forward-v1",

...r

};

}
