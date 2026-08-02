const DEFAULT_WEIGHT = 1;
const MAX_WEIGHT_CHANGE = 0.20;
const VERSION = "optimizer-v1";

function finite(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function clamp(value, minimum, maximum) {
  return Math.min(
    maximum,
    Math.max(minimum, value),
  );
}

function round(value, digits = 4) {
  if (!finite(value)) {
    return null;
  }

  const factor = 10 ** digits;

  return (
    Math.round(
      Number(value) * factor,
    ) / factor
  );
}

function normalizeMetric(metric = {}) {
  return {
    winRate:
      finite(metric.winRate)
        ? Number(metric.winRate)
        : 50,

    averageReturnPercent:
      finite(metric.averageReturnPercent)
        ? Number(
            metric.averageReturnPercent,
          )
        : 0,

    confidence:
      finite(metric.confidence)
        ? clamp(
            Number(metric.confidence),
            0,
            1,
          )
        : 0,

    sampleSize:
      finite(metric.sampleSize)
        ? Number(metric.sampleSize)
        : 0,
  };
}

function scoreMetric(metric) {

  let score = 0;

  if (metric.winRate >= 70) {
    score += 0.45;
  }
  else if (metric.winRate <= 50) {
    score -= 0.45;
  }

  if (metric.averageReturnPercent >= 3) {
    score += 0.35;
  }
  else if (
    metric.averageReturnPercent <= 0
  ) {
    score -= 0.35;
  }

  score *= metric.confidence;

  return clamp(
    score,
    -1,
    1,
  );
}

function calculateWeight(
  currentWeight,
  score,
) {

  const delta =
    score *
    MAX_WEIGHT_CHANGE;

  return round(
    currentWeight *
    (
      1 +
      delta
    ),
  );
}

function calculateImprovement(
  score,
  confidence,
) {

  return round(
    Math.abs(score) *
    confidence *
    12,
    2,
  );
}

export function optimizeWeights({

  currentWeights = {},

  learningResult = {},

} = {}) {

  const metrics =
    learningResult.metrics || {};

  const suggestions = [];

  for (
    const [
      indicator,
      rawMetric,
    ] of Object.entries(metrics)
  ) {

    const metric =
      normalizeMetric(rawMetric);

    const currentWeight =
      finite(
        currentWeights[indicator],
      )
        ? Number(
            currentWeights[indicator],
          )
        : DEFAULT_WEIGHT;

    const score =
      scoreMetric(metric);

    const suggestedWeight =
      calculateWeight(
        currentWeight,
        score,
      );

    const deltaPercent =
      round(
        (
          (
            suggestedWeight -
            currentWeight
          ) /
          currentWeight
        ) *
        100,
        2,
      );

    suggestions.push({

      indicator,

      currentWeight,

      suggestedWeight,

      deltaPercent,

      expectedImprovement:
        calculateImprovement(
          score,
          metric.confidence,
        ),

      confidence:
        metric.confidence,

      sampleSize:
        metric.sampleSize,

      score,

    });

  }

  suggestions.sort(

    (
      first,
      second,
    ) =>

      Math.abs(
        second.deltaPercent,
      ) -

      Math.abs(
        first.deltaPercent,
      ),

  );

  return {

    version: VERSION,

    createdAt:
      new Date().toISOString(),

    suggestionCount:
      suggestions.length,

    suggestions,

  };

}

export const
WeightOptimizerInternals = {

  normalizeMetric,

  scoreMetric,

  calculateWeight,

  calculateImprovement,

  clamp,

  round,

  finite,

};
export function summarizeOptimization(result = {}) {

  const suggestions =
    Array.isArray(result.suggestions)
      ? result.suggestions
      : [];

  const increased =
    suggestions.filter(
      s => s.deltaPercent > 0,
    );

  const decreased =
    suggestions.filter(
      s => s.deltaPercent < 0,
    );

  const unchanged =
    suggestions.filter(
      s => s.deltaPercent === 0,
    );

  const averageConfidence =
    suggestions.length
      ? suggestions.reduce(
          (sum, s) =>
            sum + s.confidence,
          0,
        ) /
        suggestions.length
      : 0;

  const expectedImprovement =
    suggestions.reduce(
      (sum, s) =>
        sum +
        s.expectedImprovement,
      0,
    );

  return {

    version:
      result.version,

    createdAt:
      result.createdAt,

    suggestionCount:
      suggestions.length,

    increaseCount:
      increased.length,

    decreaseCount:
      decreased.length,

    unchangedCount:
      unchanged.length,

    averageConfidence:
      round(
        averageConfidence,
        3,
      ),

    expectedImprovement:
      round(
        expectedImprovement,
        2,
      ),

  };

}

export function rankSuggestions(result = {}) {

  const suggestions =
    [...(
      result.suggestions ||
      []
    )];

  suggestions.sort(

    (
      first,
      second,
    ) =>

      second.expectedImprovement -

      first.expectedImprovement,

  );

  return suggestions;

}

export function buildOptimizationReport({

  currentWeights = {},

  learningResult = {},

} = {}) {

  const optimization =
    optimizeWeights({

      currentWeights,

      learningResult,

    });

  return {

    optimizer:
      optimization,

    summary:
      summarizeOptimization(
        optimization,
      ),

    ranking:
      rankSuggestions(
        optimization,
      ),

  };

}

export function applyOptimizedWeights({

    currentWeights = {},

    optimizerResult = {},

    maxChange = 0.20,

} = {}) {

    const next = { ...currentWeights };

    for (const suggestion of (optimizerResult.suggestions || [])) {

        const key = suggestion.indicator;

        if (!(key in next)) continue;

        const current = Number(next[key]) || 1;

        const target = Number(suggestion.suggestedWeight) || current;

        const diff = target - current;

        const limit = Math.abs(current) * maxChange;

        let applied = target;

        if (Math.abs(diff) > limit) {

            applied =
                current +
                Math.sign(diff) * limit;

        }

        next[key] = round(applied, 3);

    }

    return next;

}

export function buildAutoWeightPackage({

    currentWeights,

    learningResult,

} = {}) {

    const report =
        buildOptimizationReport({

            currentWeights,

            learningResult,

        });

    return {

        report,

        weights:
            applyOptimizedWeights({

                currentWeights,

                optimizerResult:
                    report.optimizer,

            }),

    };

}

export function createWeightSnapshot({

    weights={},

    report={}

}={}){

    return{

        version:1,

        createdAt:new Date().toISOString(),

        weights:{...weights},

        summary:report.summary||null

    };

}

export function compareWeightSnapshots(oldSnap,newSnap){

    const changes=[];

    const before=oldSnap.weights||{};

    const after=newSnap.weights||{};

    const keys=new Set([

        ...Object.keys(before),

        ...Object.keys(after)

    ]);

    for(const key of keys){

        const a=Number(before[key]||0);

        const b=Number(after[key]||0);

        if(a!==b){

            changes.push({

                indicator:key,

                before:a,

                after:b,

                delta:round(b-a,3)

            });

        }

    }

    changes.sort(

        (x,y)=>

        Math.abs(y.delta)-

        Math.abs(x.delta)

    );

    return changes;

}

export function buildWeightHistoryEntry({

    weights={},

    report={},

    source="learning"

}={}){

    return{

        id:Date.now().toString(36),

        createdAt:new Date().toISOString(),

        source,

        score:

            report.summary?.expectedImprovement ?? 0,

        confidence:

            report.summary?.averageConfidence ?? 0,

        weights:{...weights}

    };

}

export function appendWeightHistory({

    history=[],

    entry

}={}){

    const next=[

        entry,

        ...history

    ];

    next.sort(

        (a,b)=>

        new Date(b.createdAt)-

        new Date(a.createdAt)

    );

    return next.slice(0,100);

}

export function latestWeightHistory(history=[]){

    return history[0] ?? null;

}


export function calculateLearningScore(history=[]){

    if(history.length===0){

        return{

            score:0,

            confidence:0,

            trend:"NONE"

        };

    }

    const avg=

        history.reduce(

            (s,h)=>

            s+(h.score||0),

            0

        )/history.length;

    const conf=

        history.reduce(

            (s,h)=>

            s+(h.confidence||0),

            0

        )/history.length;

    let trend="FLAT";

    if(avg>=5) trend="UP";
    if(avg<=-5) trend="DOWN";

    return{

        score:round(avg,2),

        confidence:round(conf,2),

        trend

    };

}

export function buildLearningDashboard(history=[]){

    return{

        totalRuns:history.length,

        latest:

            latestWeightHistory(history),

        learning:

            calculateLearningScore(history)

    };

}


export function buildLearningSummary(history=[]){

    const dashboard =
        buildLearningDashboard(history);

    const latest =
        dashboard.latest;

    return{

        totalRuns:
            dashboard.totalRuns,

        trend:
            dashboard.learning.trend,

        score:
            dashboard.learning.score,

        confidence:
            dashboard.learning.confidence,

        latestDate:
            latest?.createdAt ?? null,

        status:
            dashboard.learning.trend==="UP"
                ?"Learning Improving"
                :dashboard.learning.trend==="DOWN"
                ?"Needs Recalibration"
                :"Stable"

    };

}

export function buildLearningReport(history=[]){

    return{

        dashboard:
            buildLearningDashboard(history),

        summary:
            buildLearningSummary(history)

    };

}


export function calculateAIAccuracy(history=[]){

    if(history.length===0){

        return{

            accuracy:0,

            total:0

        };

    }

    const wins=

        history.filter(

            h=>

            (h.score??0)>0

        ).length;

    return{

        accuracy:round(

            wins/history.length*100,

            2

        ),

        total:history.length

    };

}

export function buildAISystemStatus(history=[]){

    const learning=

        buildLearningSummary(history);

    const accuracy=

        calculateAIAccuracy(history);

    return{

        learning,

        accuracy

    };

}


export function calculateReliability(history=[]){

    if(history.length===0){

        return{

            value:0,

            grade:"N/A"

        };

    }

    const score=

        history.reduce(

            (s,h)=>

            s+(h.confidence??0),

            0

        )/history.length;

    let grade="C";

    if(score>=0.90) grade="S";
    else if(score>=0.80) grade="A";
    else if(score>=0.70) grade="B";

    return{

        value:round(score*100,2),

        grade

    };

}

export function buildAIHealth(history=[]){

    return{

        learning:

            buildLearningSummary(history),

        accuracy:

            calculateAIAccuracy(history),

        reliability:

            calculateReliability(history)

    };

}


export function calculatePerformanceIndex(history=[]){

    const health=
        buildAIHealth(history);

    const learning=
        health.learning;

    const accuracy=
        health.accuracy;

    const reliability=
        health.reliability;

    const index=round(

        learning.score*0.4+

        accuracy.accuracy*0.4+

        reliability.value*0.2,

        2

    );

    let rating="Bronze";

    if(index>=90) rating="Platinum";
    else if(index>=80) rating="Gold";
    else if(index>=70) rating="Silver";

    return{

        index,

        rating

    };

}

export function buildAIScoreBoard(history=[]){

    return{

        health:

            buildAIHealth(history),

        performance:

            calculatePerformanceIndex(history)

    };

}


export function calculateEvolutionScore(history=[]){

    if(history.length<2){

        return{

            score:0,

            direction:"NONE"

        };

    }

    const latest=history[0].score??0;

    const oldest=history.at(-1).score??0;

    const diff=round(

        latest-oldest,

        2

    );

    let direction="FLAT";

    if(diff>0) direction="UP";

    if(diff<0) direction="DOWN";

    return{

        score:diff,

        direction

    };

}

export function buildEvolutionReport(history=[]){

    return{

        ai:

            buildAIScoreBoard(history),

        evolution:

            calculateEvolutionScore(history)

    };

}


export function calculateCalibration(history=[]){

    if(history.length===0){

        return{

            calibration:0,

            state:"UNTRAINED"

        };

    }

    const avgScore=

        history.reduce(

            (s,h)=>

            s+(h.score??0),

            0

        )/history.length;

    const avgConfidence=

        history.reduce(

            (s,h)=>

            s+(h.confidence??0),

            0

        )/history.length;

    const calibration=

        round(

            (avgScore*2)+

            (avgConfidence*100),

            2

        );

    let state="LEARNING";

    if(calibration>=90){

        state="OPTIMIZED";

    }else if(calibration>=70){

        state="STABLE";

    }

    return{

        calibration,

        state

    };

}

export function buildCalibrationReport(history=[]){

    return{

        evolution:

            buildEvolutionReport(history),

        calibration:

            calculateCalibration(history)

    };

}


export function calculateAdaptiveWeights(history=[]){

    const latest=
        latestWeightHistory(history);

    if(!latest){

        return{

            multiplier:1,

            state:"DEFAULT"

        };

    }

    const learning=
        calculateLearningScore(history);

    const evolution=
        calculateEvolutionScore(history);

    let multiplier=1;

    if(learning.trend==="UP"){

        multiplier+=0.05;

    }

    if(evolution.direction==="UP"){

        multiplier+=0.05;

    }

    if(learning.trend==="DOWN"){

        multiplier-=0.05;

    }

    if(evolution.direction==="DOWN"){

        multiplier-=0.05;

    }

    multiplier=clamp(

        multiplier,

        0.8,

        1.2

    );

    return{

        multiplier:

            round(multiplier,3),

        state:

            multiplier>1

            ?"BOOST"

            :multiplier<1

            ?"REDUCE"

            :"DEFAULT"

    };

}

export function buildAdaptiveLearningReport(history=[]){

    return{

        calibration:

            buildCalibrationReport(history),

        adaptive:

            calculateAdaptiveWeights(history)

    };

}


export function evaluateBacktestReadiness(history=[]){

    const learning=
        calculateLearningScore(history);

    const calibration=
        calculateCalibration(history);

    const adaptive=
        calculateAdaptiveWeights(history);

    let ready=true;

    const reasons=[];

    if(history.length<30){

        ready=false;

        reasons.push(
            "Insufficient trade history"
        );

    }

    if(calibration.calibration<70){

        ready=false;

        reasons.push(
            "Calibration below threshold"
        );

    }

    if(learning.confidence<0.70){

        ready=false;

        reasons.push(
            "Confidence too low"
        );

    }

    return{

        ready,

        reasons,

        adaptiveMultiplier:
            adaptive.multiplier,

        calibration:
            calibration.calibration,

        confidence:
            learning.confidence

    };

}

export function buildBacktestPackage(history=[]){

    return{

        adaptive:

            buildAdaptiveLearningReport(history),

        readiness:

            evaluateBacktestReadiness(history)

    };

}


export function evaluateOptimizationGate(history=[]){

    const readiness=
        evaluateBacktestReadiness(history);

    const performance=
        calculatePerformanceIndex(history);

    const evolution=
        calculateEvolutionScore(history);

    let approved=
        readiness.ready;

    const reasons=[];

    if(!readiness.ready){

        approved=false;

        reasons.push(...readiness.reasons);

    }

    if(performance.index<75){

        approved=false;

        reasons.push(
            "Performance index below target"
        );

    }

    if(evolution.direction==="DOWN"){

        approved=false;

        reasons.push(
            "Negative evolution trend"
        );

    }

    return{

        approved,

        performanceIndex:
            performance.index,

        evolution:
            evolution.direction,

        reasons

    };

}

export function buildOptimizationPackage(history=[]){

    return{

        readiness:

            buildBacktestPackage(history),

        gate:

            evaluateOptimizationGate(history)

    };

}


export function detectMarketRegime({

    trendScore=50,

    volatilityScore=50,

    momentumScore=50

}={}){

    const score=

        round(

            trendScore*0.4+

            momentumScore*0.4-

            volatilityScore*0.2,

            2

        );

    let regime="RANGE";

    if(score>=65){

        regime="BULL";

    }else if(score<=35){

        regime="BEAR";

    }

    return{

        score,

        regime

    };

}

export function buildMarketAwareLearning(history=[],market={}){

    return{

        optimization:

            buildOptimizationPackage(history),

        market:

            detectMarketRegime(market)

    };

}


export function calculatePortfolioRisk({

    positions=[]

}={}){

    if(positions.length===0){

        return{

            risk:0,

            level:"NONE"

        };

    }

    const total=

        positions.reduce(

            (s,p)=>

            s+(p.weight??0),

            0

        );

    const avgVolatility=

        positions.reduce(

            (s,p)=>

            s+(p.volatility??0),

            0

        )/positions.length;

    const risk=

        round(

            total*

            avgVolatility,

            2

        );

    let level="LOW";

    if(risk>=70){

        level="HIGH";

    }else if(risk>=40){

        level="MEDIUM";

    }

    return{

        risk,

        level

    };

}

export function buildPortfolioAIReport({

    history=[],

    positions=[],

    market={}

}={}){

    return{

        learning:

            buildMarketAwareLearning(

                history,

                market

            ),

        portfolio:

            calculatePortfolioRisk({

                positions

            })

    };

}


export function calculatePositionSizing({

    capital=100000,

    riskPercent=1,

    stopPercent=5

}={}){

    const riskAmount=

        capital*

        (riskPercent/100);

    const position=

        stopPercent===0

        ?0

        :round(

            riskAmount/

            (stopPercent/100),

            2

        );

    return{

        capital,

        riskAmount:

            round(riskAmount,2),

        position,

        allocation:

            round(

                position/

                capital*

                100,

                2

            )

    };

}

export function buildTradingPlan({

    history=[],

    market={},

    positions=[],

    capital=100000,

    riskPercent=1,

    stopPercent=5

}={}){

    return{

        ai:

            buildPortfolioAIReport({

                history,

                market,

                positions

            }),

        sizing:

            calculatePositionSizing({

                capital,

                riskPercent,

                stopPercent

            })

    };

}


export function calculateSignalQuality({

    trend=50,

    momentum=50,

    volume=50,

    volatility=50

}={}){

    const score=

        round(

            trend*0.35+

            momentum*0.30+

            volume*0.20+

            (100-volatility)*0.15,

            2

        );

    let quality="LOW";

    if(score>=80){

        quality="A";

    }else if(score>=65){

        quality="B";

    }else if(score>=50){

        quality="C";

    }

    return{

        score,

        quality

    };

}

export function buildExecutionPackage({

    history=[],

    market={},

    positions=[],

    capital=100000,

    signal={}

}={}){

    return{

        plan:

            buildTradingPlan({

                history,

                market,

                positions,

                capital

            }),

        signal:

            calculateSignalQuality(signal)

    };

}


export function buildTradeDecision({

    signal={},

    learning={},

    market={},

    portfolio={}

}={}){

    const signalScore =
        signal.score ?? 0;

    const learningScore =
        learning.learning?.score ??
        learning.score ??
        0;

    const marketScore =
        market.score ?? 50;

    const risk =
        portfolio.risk ?? 0;

    const totalScore = round(

        signalScore*0.40+

        learningScore*0.25+

        marketScore*0.25-

        risk*0.10,

        2

    );

    let action="HOLD";

    if(totalScore>=80){

        action="STRONG BUY";

    }else if(totalScore>=65){

        action="BUY";

    }else if(totalScore<=30){

        action="SELL";

    }

    return{

        totalScore,

        action,

        confidence:

            round(

                Math.min(

                    100,

                    totalScore

                ),

                2

            )

    };

}

export function buildAISummary({

    history=[],

    signal={},

    market={},

    positions=[],

    capital=100000

}={}){

    const trading=

        buildTradingPlan({

            history,

            market,

            positions,

            capital

        });

    const learning=

        buildLearningDashboard(history);

    const portfolio=

        calculatePortfolioRisk({

            positions

        });

    const signalQuality=

        calculateSignalQuality(signal);

    return{

        trading,

        decision:

            buildTradeDecision({

                signal:signalQuality,

                learning,

                market:

                    detectMarketRegime(

                        market

                    ),

                portfolio

            })

    };

}


export function calibrateConfidence({

    prediction=50,

    accuracy=50,

    reliability=50,

    market=50

}={}){

    const confidence=

        round(

            prediction*0.35+

            accuracy*0.30+

            reliability*0.20+

            market*0.15,

            2

        );

    let grade="C";

    if(confidence>=90){

        grade="S";

    }else if(confidence>=80){

        grade="A";

    }else if(confidence>=70){

        grade="B";

    }

    return{

        confidence,

        grade

    };

}

export function buildConfidencePackage({

    history=[],

    signal={},

    market={},

    positions=[],

    capital=100000

}={}){

    const summary=

        buildAISummary({

            history,

            signal,

            market,

            positions,

            capital

        });

    const calibration=

        calibrateConfidence({

            prediction:

                summary.decision.totalScore,

            accuracy:

                calculatePerformanceIndex(history).index,

            reliability:

                calculateReliability(history).value,

            market:

                detectMarketRegime(market).score

        });

    return{

        summary,

        calibration

    };

}


export function rankOpportunities(list=[]){

    return [...list]

        .map(item=>{

            const score=

                round(

                    (item.signal??0)*0.35+

                    (item.ai??0)*0.30+

                    (item.market??0)*0.20+

                    (item.volume??0)*0.15,

                    2

                );

            return{

                ...item,

                score

            };

        })

        .sort(

            (a,b)=>

            b.score-a.score

        );

}

export function buildRankingDashboard({

    candidates=[],

    history=[],

    market={}

}={}){

    return{

        ranking:

            rankOpportunities(

                candidates

            ),

        market:

            detectMarketRegime(

                market

            ),

        learning:

            buildLearningDashboard(

                history

            )

    };

}


export function filterCandidates(list=[],{

    minScore=70,

    allowedRegimes=["BULL","RANGE"]

}={}){

    return list.filter(item=>

        (item.score??0)>=minScore &&

        allowedRegimes.includes(

            item.regime??"RANGE"

        )

    );

}

export function buildTradeCandidates({

    candidates=[],

    history=[],

    market={}

}={}){

    const ranking=

        rankOpportunities(

            candidates

        );

    const regime=

        detectMarketRegime(

            market

        );

    const enriched=

        ranking.map(item=>({

            ...item,

            regime:regime.regime

        }));

    return{

        regime,

        ranking,

        filtered:

            filterCandidates(

                enriched

            )

    };

}


export function assignExecutionPriority(list = []) {
  return list.map((item) => {
    const score = Number(item?.score ?? 0);

    let priority = "LOW";

    if (score >= 90) {
      priority = "URGENT";
    } else if (score >= 80) {
      priority = "HIGH";
    } else if (score >= 70) {
      priority = "MEDIUM";
    }

    return {
      ...item,
      priority,
    };
  });
}
export function buildExecutionQueue({

    candidates=[],

    history=[],

    market={}

}={}){

    const trade=

        buildTradeCandidates({

            candidates,

            history,

            market

        });

    return{

        ...trade,

        queue:

            assignExecutionPriority(

                trade.filtered

            )

            .sort(

                (a,b)=>

                b.score-a.score

            )

    };

}




export function calculateRiskReward({

    entry=100,

    stop=95,

    target=115

}={}){

    const risk=

        Math.max(

            entry-stop,

            0.01

        );

    const reward=

        Math.max(

            target-entry,

            0

        );

    return{

        risk:

            round(risk,2),

        reward:

            round(reward,2),

        rr:

            round(

                reward/risk,

                2

            )

    };

}

export function optimizeExecutionCandidates(list=[]){

    return list.map(item=>{

        const rr=

            calculateRiskReward({

                entry:item.entry??100,

                stop:item.stop??95,

                target:item.target??115

            });

        return{

            ...item,

            rr

        };

    }).sort(

        (a,b)=>

        b.rr.rr-a.rr.rr

    );

}


export function optimizePortfolio(candidates=[]){

    const total=

        candidates.reduce(

            (s,c)=>

            s+(c.score??0),

            0

        );

    if(total<=0){

        return [];

    }

    return candidates

        .map(c=>({

            ...c,

            allocation:

                round(

                    (c.score??0)/total*100,

                    2

                )

        }))

        .sort(

            (a,b)=>

            b.allocation-a.allocation

        );

}

export function buildPortfolioPlan({

    candidates=[]

}={}){

    return{

        portfolio:

            optimizePortfolio(

                candidates

            )

    };

}


export function allocateCapital({

    capital=100000,

    portfolio=[]

}={}){

    return portfolio.map(item=>({

        ...item,

        capital:

            round(

                capital*

                (item.allocation??0)/100,

                2

            )

    }));

}

export function buildCapitalPlan({

    capital=100000,

    candidates=[]

}={}){

    const portfolio=

        optimizePortfolio(

            candidates

        );

    return{

        portfolio,

        capitalPlan:

            allocateCapital({

                capital,

                portfolio

            })

    };

}


export function calculateExecutableShares({

  capital = 0,

  price = 0,

  lotSize = 100,

} = {}) {

  const safeCapital =
    Math.max(
      0,
      Number(capital) || 0,
    );

  const safePrice =
    Math.max(
      0,
      Number(price) || 0,
    );

  const safeLotSize =
    Math.max(
      1,
      Math.floor(
        Number(lotSize) || 100,
      ),
    );

  if (
    safeCapital <= 0 ||
    safePrice <= 0
  ) {

    return {

      shares: 0,

      lots: 0,

      investedAmount: 0,

      remainingCapital:
        round(
          safeCapital,
          2,
        ),

    };

  }

  const affordableShares =
    Math.floor(
      safeCapital /
      safePrice,
    );

  const lots =
    Math.floor(
      affordableShares /
      safeLotSize,
    );

  const shares =
    lots *
    safeLotSize;

  const investedAmount =
    round(
      shares *
      safePrice,
      2,
    );

  return {

    shares,

    lots,

    investedAmount,

    remainingCapital:
      round(
        safeCapital -
        investedAmount,
        2,
      ),

  };

}

export function buildExecutableCapitalPlan({

  capital = 100000,

  candidates = [],

  lotSize = 100,

} = {}) {

  const plan =
    buildCapitalPlan({

      capital,

      candidates,

    });

  const executions =
    plan.capitalPlan.map(
      (item) => {

        const execution =
          calculateExecutableShares({

            capital:
              item.capital,

            price:
              item.price,

            lotSize:
              item.lotSize ??
              lotSize,

          });

        return {

          ...item,

          ...execution,

          executable:
            execution.shares > 0,

        };

      },
    );

  return {

    ...plan,

    executions,

    totalInvested:
      round(
        executions.reduce(
          (
            sum,
            item,
          ) =>
            sum +
            item.investedAmount,
          0,
        ),
        2,
      ),

    remainingCapital:
      round(
        Number(capital) -
        executions.reduce(
          (
            sum,
            item,
          ) =>
            sum +
            item.investedAmount,
          0,
        ),
        2,
      ),

  };

}


export function rebalancePortfolio({

    portfolio=[],

    targetAllocation=[]

}={}){

    return portfolio.map(position=>{

        const target=

            targetAllocation.find(

                t=>t.code===position.code

            );

        const current=

            Number(position.allocation??0);

        const desired=

            Number(target?.allocation??current);

        const delta=

            round(

                desired-current,

                2

            );

        return{

            ...position,

            targetAllocation:desired,

            delta,

            action:

                delta>1

                ?"BUY"

                :delta<-1

                ?"SELL"

                :"HOLD"

        };

    });

}

export function buildRebalancePlan({

    portfolio=[],

    targetAllocation=[]

}={}){

    return{

        rebalance:

            rebalancePortfolio({

                portfolio,

                targetAllocation

            })

    };

}


export function calculatePerformanceMetrics({

    trades=[]

}={}){

    const total=

        trades.length;

    const wins=

        trades.filter(

            t=>

            (t.pnl??0)>0

        ).length;

    const losses=

        total-wins;

    const profit=

        trades.reduce(

            (s,t)=>

            s+

            (t.pnl??0),

            0

        );

    const winRate=

        total===0

        ?0

        :round(

            wins/

            total*

            100,

            2

        );

    const averagePnL=

        total===0

        ?0

        :round(

            profit/

            total,

            2

        );

    return{

        total,

        wins,

        losses,

        profit:

            round(profit,2),

        winRate,

        averagePnL

    };

}

export function buildPerformanceDashboard({

    trades=[]

}={}){

    return{

        metrics:

            calculatePerformanceMetrics({

                trades

            })

    };

}


export function calculateDrawdown({

  trades = [],

  initialEquity = 100000,

} = {}) {

  let equity =
    Number(initialEquity) || 0;

  let peak =
    equity;

  let maximumDrawdown =
    0;

  let maximumDrawdownPercent =
    0;

  const curve = [];

  trades.forEach(
    (
      trade,
      index,
    ) => {

      const pnl =
        Number(
          trade?.pnl ?? 0,
        ) || 0;

      equity += pnl;

      peak =
        Math.max(
          peak,
          equity,
        );

      const drawdown =
        peak - equity;

      const drawdownPercent =
        peak > 0
          ? (
              drawdown /
              peak
            ) * 100
          : 0;

      maximumDrawdown =
        Math.max(
          maximumDrawdown,
          drawdown,
        );

      maximumDrawdownPercent =
        Math.max(
          maximumDrawdownPercent,
          drawdownPercent,
        );

      curve.push({

        index,

        equity:
          round(
            equity,
            2,
          ),

        peak:
          round(
            peak,
            2,
          ),

        drawdown:
          round(
            drawdown,
            2,
          ),

        drawdownPercent:
          round(
            drawdownPercent,
            2,
          ),

      });

    },
  );

  return {

    initialEquity:
      round(
        initialEquity,
        2,
      ),

    finalEquity:
      round(
        equity,
        2,
      ),

    maximumDrawdown:
      round(
        maximumDrawdown,
        2,
      ),

    maximumDrawdownPercent:
      round(
        maximumDrawdownPercent,
        2,
      ),

    curve,

  };

}

export function calculateProfitFactor({

  trades = [],

} = {}) {

  const grossProfit =
    trades
      .filter(
        (trade) =>
          Number(
            trade?.pnl ?? 0,
          ) > 0,
      )
      .reduce(
        (
          sum,
          trade,
        ) =>
          sum +
          Number(
            trade.pnl,
          ),
        0,
      );

  const grossLoss =
    Math.abs(
      trades
        .filter(
          (trade) =>
            Number(
              trade?.pnl ?? 0,
            ) < 0,
        )
        .reduce(
          (
            sum,
            trade,
          ) =>
            sum +
            Number(
              trade.pnl,
            ),
          0,
        ),
    );

  const profitFactor =
    grossLoss > 0
      ? grossProfit /
        grossLoss
      : grossProfit > 0
        ? Infinity
        : 0;

  return {

    grossProfit:
      round(
        grossProfit,
        2,
      ),

    grossLoss:
      round(
        grossLoss,
        2,
      ),

    profitFactor:
      Number.isFinite(
        profitFactor,
      )
        ? round(
            profitFactor,
            3,
          )
        : Infinity,

  };

}

export function buildRiskPerformanceReport({

  trades = [],

  initialEquity = 100000,

} = {}) {

  return {

    performance:
      calculatePerformanceMetrics({

        trades,

      }),

    drawdown:
      calculateDrawdown({

        trades,

        initialEquity,

      }),

    profitFactor:
      calculateProfitFactor({

        trades,

      }),

  };

}


export function buildEquityCurve({

    trades=[],

    initialEquity=100000

}={}){

    let equity=initialEquity;

    const curve=[];

    let peak=equity;

    let trough=equity;

    for(let i=0;i<trades.length;i++){

        equity+=Number(trades[i].pnl??0);

        peak=Math.max(peak,equity);

        trough=Math.min(trough,equity);

        curve.push({

            trade:i+1,

            equity:round(equity,2),

            peak:round(peak,2),

            trough:round(trough,2)

        });

    }

    return{

        initialEquity,

        finalEquity:round(equity,2),

        highestEquity:round(peak,2),

        lowestEquity:round(trough,2),

        curve

    };

}

export function calculateRecoveryFactor({

    trades=[],

    initialEquity=100000

}={}){

    const dd=

        calculateDrawdown({

            trades,

            initialEquity

        });

    const profit=

        trades.reduce(

            (s,t)=>

                s+(t.pnl??0),

            0

        );

    const recovery=

        dd.maximumDrawdown===0

        ?0

        :round(

            profit/

            dd.maximumDrawdown,

            3

        );

    return{

        recovery,

        maximumDrawdown:

            dd.maximumDrawdown

    };

}

export function buildEquityDashboard({

    trades=[],

    initialEquity=100000

}={}){

    return{

        equity:

            buildEquityCurve({

                trades,

                initialEquity

            }),

        recovery:

            calculateRecoveryFactor({

                trades,

                initialEquity

            })

    };

}


export function runMonteCarloSimulation({

    trades=[],

    initialCapital=100000,

    simulations=100

}={}){

    const pnls=

        trades.map(

            t=>Number(t.pnl??0)

        );

    if(pnls.length===0){

        return{

            simulations:0,

            averageFinalCapital:initialCapital,

            bestCase:initialCapital,

            worstCase:initialCapital

        };

    }

    const results=[];

    for(let s=0;s<simulations;s++){

        let capital=initialCapital;

        const shuffled=[...pnls].sort(

            ()=>Math.random()-0.5

        );

        for(const pnl of shuffled){

            capital+=pnl;

        }

        results.push(capital);

    }

    const average=

        results.reduce(

            (a,b)=>a+b,

            0

        )/results.length;

    return{

        simulations,

        averageFinalCapital:

            round(average,2),

        bestCase:

            round(

                Math.max(...results),

                2

            ),

        worstCase:

            round(

                Math.min(...results),

                2

            )

    };

}

export function buildSimulationDashboard({

    trades=[],

    initialCapital=100000

}={})

{

    return{

        simulation:

            runMonteCarloSimulation({

                trades,

                initialCapital

            }),

        equity:

            buildEquityDashboard({

                trades,

                initialEquity:

                    initialCapital

            })

    };

}


export function runWalkForwardValidation({

    trades=[],

    windowSize=20

}={}){

    const windows=[];

    if(windowSize<=0){

        return{

            windows,

            averagePnL:0,

            averageWinRate:0

        };

    }

    for(

        let i=0;

        i<trades.length;

        i+=windowSize

    ){

        const slice=

            trades.slice(

                i,

                i+windowSize

            );

        if(slice.length===0) continue;

        const pnl=

            slice.reduce(

                (s,t)=>

                    s+

                    Number(t.pnl??0),

                0

            );

        const wins=

            slice.filter(

                t=>

                Number(t.pnl??0)>0

            ).length;

        windows.push({

            trades:

                slice.length,

            pnl:

                round(pnl,2),

            winRate:

                round(

                    wins/

                    slice.length*

                    100,

                    2

                )

        });

    }

    return{

        windows,

        averagePnL:

            round(

                windows.reduce(

                    (s,w)=>s+w.pnl,

                    0

                )/

                Math.max(

                    windows.length,

                    1

                ),

                2

            ),

        averageWinRate:

            round(

                windows.reduce(

                    (s,w)=>

                        s+w.winRate,

                    0

                )/

                Math.max(

                    windows.length,

                    1

                ),

                2

            )

    };

}

export function buildValidationDashboard({

    trades=[]

}={}){

    return{

        validation:

            runWalkForwardValidation({

                trades

            }),

        simulation:

            buildSimulationDashboard({

                trades

            })

    };

}


export function compareStrategyPerformance({

  currentTrades = [],

  candidateTrades = [],

  initialEquity = 100000,

} = {}) {

  const current = {

    performance:
      calculatePerformanceMetrics({

        trades:
          currentTrades,

      }),

    profitFactor:
      calculateProfitFactor({

        trades:
          currentTrades,

      }),

    drawdown:
      calculateDrawdown({

        trades:
          currentTrades,

        initialEquity,

      }),

  };

  const candidate = {

    performance:
      calculatePerformanceMetrics({

        trades:
          candidateTrades,

      }),

    profitFactor:
      calculateProfitFactor({

        trades:
          candidateTrades,

      }),

    drawdown:
      calculateDrawdown({

        trades:
          candidateTrades,

        initialEquity,

      }),

  };

  const winRateDelta =
    round(

      candidate.performance.winRate -

      current.performance.winRate,

      2,

    );

  const profitDelta =
    round(

      candidate.performance.profit -

      current.performance.profit,

      2,

    );

  const drawdownDelta =
    round(

      candidate.drawdown
        .maximumDrawdownPercent -

      current.drawdown
        .maximumDrawdownPercent,

      2,

    );

  const currentPf =
    Number.isFinite(

      current.profitFactor
        .profitFactor,

    )
      ? current.profitFactor
          .profitFactor
      : 999;

  const candidatePf =
    Number.isFinite(

      candidate.profitFactor
        .profitFactor,

    )
      ? candidate.profitFactor
          .profitFactor
      : 999;

  const profitFactorDelta =
    round(

      candidatePf -
      currentPf,

      3,

    );

  const improvementScore =
    round(

      winRateDelta * 0.3 +

      profitFactorDelta * 10 * 0.3 +

      (
        profitDelta /
        Math.max(
          initialEquity,
          1,
        ) *
        100
      ) * 0.3 -

      Math.max(
        0,
        drawdownDelta,
      ) * 0.1,

      3,

    );

  const approved =

    candidateTrades.length >= 10 &&

    improvementScore > 0 &&

    profitDelta >= 0 &&

    drawdownDelta <= 2;

  const reasons = [];

  if (
    candidateTrades.length < 10
  ) {

    reasons.push(
      "Insufficient candidate trades",
    );

  }

  if (
    improvementScore <= 0
  ) {

    reasons.push(
      "No measurable improvement",
    );

  }

  if (
    profitDelta < 0
  ) {

    reasons.push(
      "Candidate profit decreased",
    );

  }

  if (
    drawdownDelta > 2
  ) {

    reasons.push(
      "Drawdown increased beyond limit",
    );

  }

  return {

    current,

    candidate,

    deltas: {

      winRate:
        winRateDelta,

      profit:
        profitDelta,

      profitFactor:
        profitFactorDelta,

      maximumDrawdownPercent:
        drawdownDelta,

    },

    improvementScore,

    approved,

    reasons,

  };

}

export function buildOptimizerValidationReport({

  currentTrades = [],

  candidateTrades = [],

  currentWeights = {},

  candidateWeights = {},

  initialEquity = 100000,

} = {}) {

  return {

    version:
      "optimizer-validation-v1",

    generatedAt:
      new Date().toISOString(),

    comparison:
      compareStrategyPerformance({

        currentTrades,

        candidateTrades,

        initialEquity,

      }),

    weightChanges:
      compareWeightSnapshots(

        {
          weights:
            currentWeights,
        },

        {
          weights:
            candidateWeights,
        },

      ),

  };

}


let weightVersionSequence = 0;

function createWeightVersionId() {
  weightVersionSequence += 1;

  const randomPart =
    globalThis.crypto?.randomUUID?.() ??
    Math.random()
      .toString(36)
      .slice(2, 10);

  return [
    "wv",
    Date.now().toString(36),
    weightVersionSequence.toString(36),
    randomPart,
  ].join("-");
}

export function createWeightVersion({
  weights = {},
  score = 0,
  notes = "",
} = {}) {
  return {
    id: createWeightVersionId(),

    createdAt:
      new Date().toISOString(),

    score:
      round(score, 2),

    notes,

    weights:
      typeof structuredClone === "function"
        ? structuredClone(weights)
        : JSON.parse(
            JSON.stringify(weights),
          ),
  };
}
export function compareWeightVersions(

    previous,

    current

){

    const diff=[];

    const keys=new Set([

        ...Object.keys(

            previous?.weights??{}

        ),

        ...Object.keys(

            current?.weights??{}

        )

    ]);

    for(const key of keys){

        const before=

            Number(

                previous?.weights?.[key]??0

            );

        const after=

            Number(

                current?.weights?.[key]??0

            );

        if(before!==after){

            diff.push({

                indicator:key,

                before,

                after,

                delta:

                    round(

                        after-before,

                        4

                    )

            });

        }

    }

    return diff.sort(

        (a,b)=>

        Math.abs(b.delta)-

        Math.abs(a.delta)

    );

}

export function buildVersionHistory({

    history=[],

    version

}={}){

    return[

        version,

        ...history

    ].slice(0,100);

}


export function rollbackWeightVersion({

    history=[],

    versionId

}={}){

    const version=

        history.find(

            h=>h.id===versionId

        );

    if(!version){

        return null;

    }

    return{

        restoredAt:

            new Date().toISOString(),

        restoredVersion:

            version.id,

        weights:

            structuredClone

                ?structuredClone(version.weights)

                :JSON.parse(

                    JSON.stringify(version.weights)

                )

    };

}

export function getLatestWeightVersion(history=[]){

    return history.length

        ?history[0]

        :null;

}

export function evaluateWeightVersion(version){

    const weights=

        Object.values(

            version?.weights??{}

        );

    if(weights.length===0){

        return{

            score:0,

            status:"EMPTY"

        };

    }

    const avg=

        weights.reduce(

            (s,w)=>

                s+Number(w),

            0

        )/

        weights.length;

    let status="NORMAL";

    if(avg>1.1){

        status="AGGRESSIVE";

    }else if(avg<0.9){

        status="DEFENSIVE";

    }

    return{

        score:

            round(avg,3),

        status

    };

}


export function createModelSnapshot({

    weights={},

    metrics={},

    note=""

}={}){

    return{

        id:

            "snapshot-"+

            crypto.randomUUID(),

        createdAt:

            new Date().toISOString(),

        note,

        weights:

            structuredClone(weights),

        metrics:

            structuredClone(metrics)

    };

}

export function restoreModelSnapshot({

    snapshot

}={}){

    return{

        weights:

            structuredClone(

                snapshot.weights

            ),

        metrics:

            structuredClone(

                snapshot.metrics

            )

    };

}

export function compareSnapshots(

    before,

    after

){

    const keys=new Set([

        ...Object.keys(

            before.metrics

        ),

        ...Object.keys(

            after.metrics

        )

    ]);

    const diff=[];

    for(const key of keys){

        diff.push({

            metric:key,

            before:

                before.metrics[key]??0,

            after:

                after.metrics[key]??0,

            delta:

                round(

                    (after.metrics[key]??0)-

                    (before.metrics[key]??0),

                    4

                )

        });

    }

    return diff;

}


export function registerModel({

    registry=[],

    snapshot

}={}){

    return[

        snapshot,

        ...registry

    ].slice(0,200);

}

export function getLatestModel(

    registry=[]

){

    return registry.length

        ?registry[0]

        :null;

}

export function findModelById({

    registry=[],

    id

}={}){

    return registry.find(

        m=>m.id===id

    )??null;

}

export function deleteModel({

    registry=[],

    id

}={}){

    return registry.filter(

        m=>m.id!==id

    );

}


export function evaluateModelPromotion({

  validationReport = {},

  humanApproval = false,

} = {}) {

  const comparison =
    validationReport?.comparison ?? {};

  const approvedByBacktest =
    comparison.approved === true;

  const reasons = [
    ...(
      Array.isArray(
        comparison.reasons,
      )
        ? comparison.reasons
        : []
    ),
  ];

  if (!approvedByBacktest) {
    reasons.push(
      "Backtest validation not approved",
    );
  }

  if (humanApproval !== true) {
    reasons.push(
      "Human approval required",
    );
  }

  const approved =
    approvedByBacktest &&
    humanApproval === true;

  return {
    approved,

    approvedByBacktest,

    humanApproval:
      humanApproval === true,

    improvementScore:
      Number(
        comparison.improvementScore ?? 0,
      ),

    reasons:
      [...new Set(reasons)],
  };

}

export function promoteModelCandidate({

  registry = [],

  currentWeights = {},

  candidateWeights = {},

  validationReport = {},

  humanApproval = false,

  note = "",

} = {}) {

  const gate =
    evaluateModelPromotion({

      validationReport,

      humanApproval,

    });

  if (!gate.approved) {
    return {
      promoted: false,

      gate,

      registry:
        [...registry],

      activeModel:
        getLatestModel(registry),

    };
  }

  const snapshot =
    createModelSnapshot({

      weights:
        candidateWeights,

      metrics: {
        improvementScore:
          gate.improvementScore,

        validationApproved:
          gate.approvedByBacktest,

      },

      note:
        note ||
        "Validated optimizer promotion",

    });

  const nextRegistry =
    registerModel({

      registry,

      snapshot,

    });

  return {
    promoted: true,

    gate,

    snapshot,

    registry:
      nextRegistry,

    activeModel:
      getLatestModel(
        nextRegistry,
      ),

    previousWeights: {
      ...currentWeights,
    },

    activeWeights: {
      ...candidateWeights,
    },

  };

}

export function rejectModelCandidate({

  registry = [],

  validationReport = {},

  reason = "Rejected by user",

} = {}) {

  return {
    promoted: false,

    rejected: true,

    rejectedAt:
      new Date().toISOString(),

    reason,

    improvementScore:
      Number(
        validationReport
          ?.comparison
          ?.improvementScore ?? 0,
      ),

    registry:
      [...registry],

    activeModel:
      getLatestModel(registry),

  };

}


export function decideLearningAction({

    comparison={},

    thresholds={}

}={}){

    const {

        improvementScore=0,

        approved=false,

        reasons=[]

    }=comparison;

    const {

        minScore=1,

        retrainScore=-1

    }=thresholds;

    if(

        approved &&

        improvementScore>=minScore

    ){

        return{

            action:"PROMOTE",

            confidence:"HIGH",

            reasons

        };

    }

    if(

        improvementScore<=

        retrainScore

    ){

        return{

            action:"RETRAIN",

            confidence:"HIGH",

            reasons

        };

    }

    return{

        action:"HOLD",

        confidence:"MEDIUM",

        reasons

    };

}

export function buildLearningDecisionReport({

    validationReport={},

    thresholds={}

}={}){

    return{

        generatedAt:

            new Date().toISOString(),

        decision:

            decideLearningAction({

                comparison:

                    validationReport.comparison??{},

                thresholds

            }),

        comparison:

            validationReport.comparison??{}

    };

}


export function executeLearningCycle({

    registry=[],

    validationReport={},

    currentWeights={},

    candidateWeights={},

    humanApproval=false

}={}){

    const decision=

        buildLearningDecisionReport({

            validationReport

        });

    let result=null;

    switch(

        decision.decision.action

    ){

        case "PROMOTE":

            result=

                promoteModelCandidate({

                    registry,

                    currentWeights,

                    candidateWeights,

                    validationReport,

                    humanApproval

                });

            break;

        case "RETRAIN":

            result={

                retraining:true,

                promoted:false,

                registry,

                reason:"Retraining required"

            };

            break;

        default:

            result={

                promoted:false,

                registry,

                reason:"Hold"

            };

    }

    return{

        cycleAt:

            new Date().toISOString(),

        decision,

        result

    };

}

export function summarizeLearningCycle(cycle={}){

    return{

        promoted:

            cycle.result?.promoted??false,

        retraining:

            cycle.result?.retraining??false,

        action:

            cycle.decision?.decision?.action??

            "UNKNOWN",

        registrySize:

            cycle.result?.registry?.length??0

    };

}


export function createLearningAuditEntry({

  cycle = {},

  source = "manual",

} = {}) {

  const summary =
    summarizeLearningCycle(
      cycle,
    );

  return {

    id:
      globalThis.crypto
        ?.randomUUID?.() ??
      [
        "audit",
        Date.now()
          .toString(36),
        Math.random()
          .toString(36)
          .slice(2, 10),
      ].join("-"),

    createdAt:
      new Date()
        .toISOString(),

    source,

    action:
      summary.action,

    promoted:
      summary.promoted,

    retraining:
      summary.retraining,

    registrySize:
      summary.registrySize,

    improvementScore:
      Number(
        cycle
          ?.decision
          ?.comparison
          ?.improvementScore ??
        0,
      ),

    reasons:
      Array.isArray(
        cycle
          ?.decision
          ?.decision
          ?.reasons,
      )
        ? [
            ...cycle
              .decision
              .decision
              .reasons,
          ]
        : [],

  };

}

export function appendLearningAuditHistory({

  history = [],

  entry,

  limit = 200,

} = {}) {

  const safeHistory =
    Array.isArray(history)
      ? history
      : [];

  if (!entry) {
    return [
      ...safeHistory,
    ];
  }

  const safeLimit =
    Math.max(
      1,
      Math.floor(
        Number(limit) ||
        200,
      ),
    );

  const merged =
    [
      entry,
      ...safeHistory,
    ];

  const unique =
    Array.from(
      new Map(
        merged.map(
          (item) => [
            item.id,
            item,
          ],
        ),
      ).values(),
    );

  return unique
    .sort(
      (
        first,
        second,
      ) =>
        new Date(
          second.createdAt,
        ) -
        new Date(
          first.createdAt,
        ),
    )
    .slice(
      0,
      safeLimit,
    );

}

export function summarizeLearningAuditHistory(

  history = [],

) {

  const safeHistory =
    Array.isArray(history)
      ? history
      : [];

  const promotedCount =
    safeHistory.filter(
      (entry) =>
        entry.promoted === true,
    ).length;

  const retrainingCount =
    safeHistory.filter(
      (entry) =>
        entry.retraining === true,
    ).length;

  const holdCount =
    safeHistory.filter(
      (entry) =>
        entry.action === "HOLD",
    ).length;

  const averageImprovement =
    safeHistory.length > 0
      ? safeHistory.reduce(
          (
            sum,
            entry,
          ) =>
            sum +
            Number(
              entry
                .improvementScore ??
              0,
            ),
          0,
        ) /
        safeHistory.length
      : 0;

  return {

    totalRuns:
      safeHistory.length,

    promotedCount,

    retrainingCount,

    holdCount,

    promotionRate:
      safeHistory.length > 0
        ? round(
            (
              promotedCount /
              safeHistory.length
            ) *
            100,
            2,
          )
        : 0,

    averageImprovement:
      round(
        averageImprovement,
        3,
      ),

    latest:
      safeHistory[0] ??
      null,

  };

}

export function buildLearningAuditReport({

  history = [],

  cycle,

  source = "manual",

} = {}) {

  const entry =
    createLearningAuditEntry({

      cycle,

      source,

    });

  const nextHistory =
    appendLearningAuditHistory({

      history,

      entry,

    });

  return {

    entry,

    history:
      nextHistory,

    summary:
      summarizeLearningAuditHistory(
        nextHistory,
      ),

  };

}


export function evaluateWeightHealth({

    weights={},

    warningThreshold=0.30

}={}){

    const warnings=[];

    for(const [name,value] of Object.entries(weights)){

        const v=Number(value);

        if(!Number.isFinite(v)){

            warnings.push({

                indicator:name,

                level:"ERROR",

                message:"Invalid weight"

            });

            continue;

        }

        if(v<0){

            warnings.push({

                indicator:name,

                level:"ERROR",

                message:"Negative weight"

            });

        }

        if(Math.abs(v-1)>=warningThreshold){

            warnings.push({

                indicator:name,

                level:"WARNING",

                message:"Large deviation"

            });

        }

    }

    return{

        healthy:

            warnings.filter(

                w=>w.level==="ERROR"

            ).length===0,

        warnings

    };

}

export function buildWeightHealthReport({

    weights={},

    history=[]

}={}){

    return{

        health:

            evaluateWeightHealth({

                weights

            }),

        learning:

            buildLearningSummary(

                history

            )

    };

}


export function normalizeWeights({

    weights={},

    minimum=0.1,

    maximum=2.0,

    targetAverage=1

}={}){

    const normalized={};

    const values=[];

    for(const [key,value] of Object.entries(weights)){

        let v=Number(value);

        if(!Number.isFinite(v)){

            v=targetAverage;

        }

        v=Math.max(

            minimum,

            Math.min(

                maximum,

                v

            )

        );

        normalized[key]=v;

        values.push(v);

    }

    if(values.length===0){

        return normalized;

    }

    const average=

        values.reduce(

            (a,b)=>a+b,

            0

        )/

        values.length;

    const factor=

        targetAverage/

        average;

    for(const key of Object.keys(normalized)){

        normalized[key]=

            round(

                Math.max(

                    minimum,

                    Math.min(

                        maximum,

                        normalized[key]*factor

                    )

                ),

                4

            );

    }

    return normalized;

}

export function buildNormalizedWeightReport({

    weights={},

    history=[]

}={}){

    const normalized=

        normalizeWeights({

            weights

        });

    return{

        original:weights,

        normalized,

        health:

            evaluateWeightHealth({

                weights:normalized

            }),

        learning:

            buildLearningSummary(

                history

            )

    };

}


export function buildSelfEvolutionPlan({

    history=[],

    currentWeights={},

    learningResult={},

    currentTrades=[],

    candidateTrades=[],

    registry=[],

    humanApproval=false

}={}){

    const optimization=

        buildAutoWeightPackage({

            currentWeights,

            learningResult

        });

    const optimizedWeightCount =
        Object.keys(
            optimization.weights ?? {}
        ).length;

    const normalizedWeights =
        optimizedWeightCount <= 1
            ? {
                ...optimization.weights
              }
            : normalizeWeights({
                weights:
                    optimization.weights
              });

    const validationReport=

        buildOptimizerValidationReport({

            currentTrades,

            candidateTrades,

            currentWeights,

            candidateWeights:

                normalizedWeights

        });

    const cycle=

        executeLearningCycle({

            registry,

            validationReport,

            currentWeights,

            candidateWeights:

                normalizedWeights,

            humanApproval

        });

    const audit=

        buildLearningAuditReport({

            history:[],

            cycle,

            source:

                "self-evolution"

        });

    return{

        generatedAt:

            new Date().toISOString(),

        optimization,

        normalizedWeights,

        validationReport,

        cycle,

        audit,

        health:

            evaluateWeightHealth({

                weights:

                    normalizedWeights

            })

    };

}

export function summarizeSelfEvolutionPlan(plan={}){

    return{

        promoted:

            plan.cycle
                ?.result
                ?.promoted ?? false,

        action:

            plan.cycle
                ?.decision
                ?.decision
                ?.action ?? "UNKNOWN",

        improvementScore:

            plan.validationReport
                ?.comparison
                ?.improvementScore ?? 0,

        approvedByBacktest:

            plan.validationReport
                ?.comparison
                ?.approved ?? false,

        weightHealth:

            plan.health
                ?.healthy ?? false,

        changedIndicators:

            plan.validationReport
                ?.weightChanges
                ?.length ?? 0

    };

}


export function buildLearningSchedule({

    intervalHours=24,

    lastRunAt=null,

    enabled=true

}={}){

    const now=new Date();

    const last=

        lastRunAt

        ?new Date(lastRunAt)

        :now;

    const next=

        new Date(

            last.getTime()+

            intervalHours*

            60*

            60*

            1000

        );

    return{

        enabled,

        intervalHours,

        lastRunAt:

            last.toISOString(),

        nextRunAt:

            next.toISOString(),

        waiting:

            next>now

    };

}

export function shouldRunLearning({

    schedule

}={}){

    if(

        !schedule?.enabled

    ){

        return false;

    }

    return(

        new Date(

            schedule.nextRunAt

        )<=new Date()

    );

}

export function buildContinuousLearningReport({

    schedule,

    cycle

}={}){

    return{

        schedule,

        ready:

            shouldRunLearning({

                schedule

            }),

        summary:

            summarizeLearningCycle(

                cycle

            )

    };

}

