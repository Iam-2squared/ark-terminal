function num(v,d=0){
    const n=Number(v);
    return Number.isFinite(n)?n:d;
}

export function detectMarketRegime({

    trendScore=0,
    volatility=20,
    adx=20,
    rsi=50,
    vix=20

}={}){

    trendScore=num(trendScore);
    volatility=num(volatility);
    adx=num(adx);
    rsi=num(rsi);
    vix=num(vix);

    let regime="RANGE";

    if(
        trendScore>=70 &&
        adx>=25 &&
        rsi>=55 &&
        vix<25
    ){
        regime="BULL";
    }

    else if(
        trendScore<=30 &&
        adx>=25 &&
        rsi<=45
    ){
        regime="BEAR";
    }

    else if(
        volatility>=40 ||
        vix>=35
    ){
        regime="HIGH_VOLATILITY";
    }

    else if(
        volatility<=15 &&
        vix<=15
    ){
        regime="LOW_VOLATILITY";
    }

    return{
        regime,
        trendScore,
        volatility,
        adx,
        rsi,
        vix
    };
}

export function regimeRecommendation({

    regime="RANGE"

}={}){

    const map={

        BULL:
        "Trend Following",

        BEAR:
        "Defensive",

        RANGE:
        "Swing Trade",

        HIGH_VOLATILITY:
        "Reduce Position",

        LOW_VOLATILITY:
        "Breakout Watch"

    };

    return{

        regime,

        recommendation:
            map[regime] ??
            "Neutral"

    };

}
