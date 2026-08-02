import assert from "node:assert/strict";
import test from "node:test";

import {
  optimizeWeights,
  summarizeOptimization,
  rankSuggestions,
  buildAutoWeightPackage,
  createWeightSnapshot,
  compareWeightSnapshots,
  buildWeightHistoryEntry,
  appendWeightHistory,
  latestWeightHistory,
  calculateLearningScore,
  buildLearningDashboard,
  buildLearningSummary,
  buildLearningReport,
  calculateAIAccuracy,
  buildAISystemStatus,
  calculateReliability,
  buildAIHealth,
  calculatePerformanceIndex,
  buildAIScoreBoard,
  calculateEvolutionScore,
  buildEvolutionReport,
  calculateCalibration,
  buildCalibrationReport,
  calculateAdaptiveWeights,
  buildAdaptiveLearningReport,
  evaluateBacktestReadiness,
  buildBacktestPackage,
  evaluateOptimizationGate,
  buildOptimizationPackage,
  detectMarketRegime,
  buildMarketAwareLearning,
  calculatePortfolioRisk,
  buildPortfolioAIReport,
  calculatePositionSizing,
  buildTradingPlan,
  calculateSignalQuality,
  buildExecutionPackage,
  buildTradeDecision,
  buildAISummary,
  calibrateConfidence,
  buildConfidencePackage,
  rankOpportunities,
  buildRankingDashboard,
  filterCandidates,
  buildTradeCandidates,
  assignExecutionPriority,
  calculateRiskReward,
  optimizeExecutionCandidates,
  optimizePortfolio,
  buildPortfolioPlan,
  allocateCapital,
  buildCapitalPlan,
  calculateExecutableShares,
  buildExecutableCapitalPlan,
  rebalancePortfolio,
  buildRebalancePlan,
  calculatePerformanceMetrics,
  buildPerformanceDashboard,
  calculateDrawdown,
  calculateProfitFactor,
  buildRiskPerformanceReport,
  buildEquityCurve,
  calculateRecoveryFactor,
  buildEquityDashboard,
  runMonteCarloSimulation,
  buildSimulationDashboard,
  runWalkForwardValidation,
  compareStrategyPerformance,
  buildOptimizerValidationReport,
  createWeightVersion,
  compareWeightVersions,
  buildVersionHistory,
  createModelSnapshot,
  restoreModelSnapshot,
  compareSnapshots,
  registerModel,
  getLatestModel,
  findModelById,
  deleteModel,
  evaluateModelPromotion,
  promoteModelCandidate,
  rejectModelCandidate,
  decideLearningAction,
  buildLearningDecisionReport,
  executeLearningCycle,
  summarizeLearningCycle,
  createLearningAuditEntry,
  appendLearningAuditHistory,
  summarizeLearningAuditHistory,
  buildLearningAuditReport,
  evaluateWeightHealth,
  buildWeightHealthReport,
  normalizeWeights,
  buildNormalizedWeightReport,
  buildSelfEvolutionPlan,
  summarizeSelfEvolutionPlan,
  buildLearningSchedule,
  shouldRunLearning,
  buildContinuousLearningReport,
  rollbackWeightVersion,
  getLatestWeightVersion,
  evaluateWeightVersion,
  buildValidationDashboard,
  buildExecutionQueue,
  buildOptimizationReport,
} from "../learning/weight-optimizer.js";

test("optimizer increases strong indicator", () => {

  const result =
    optimizeWeights({

      currentWeights: {
        rsi: 1,
      },

      learningResult: {

        metrics: {

          rsi: {

            winRate: 76,

            averageReturnPercent: 5,

            confidence: 0.9,

            sampleSize: 40,

          },

        },

      },

    });

  assert.equal(
    result.suggestions.length,
    1,
  );

  assert.ok(
    result.suggestions[0]
      .suggestedWeight > 1,
  );

});

test("optimizer decreases weak indicator", () => {

  const result =
    optimizeWeights({

      currentWeights: {
        macd: 1,
      },

      learningResult: {

        metrics: {

          macd: {

            winRate: 43,

            averageReturnPercent: -2,

            confidence: 1,

            sampleSize: 60,

          },

        },

      },

    });

  assert.ok(
    result.suggestions[0]
      .suggestedWeight < 1,
  );

});

test("summary is generated", () => {

  const report =
    buildOptimizationReport({

      currentWeights: {
        rsi: 1,
      },

      learningResult: {

        metrics: {

          rsi: {

            winRate: 80,

            averageReturnPercent: 6,

            confidence: 1,

            sampleSize: 80,

          },

        },

      },

    });

  assert.equal(
    report.summary.suggestionCount,
    1,
  );

});

test("ranking sorts correctly", () => {

  const ranking =
    rankSuggestions({

      suggestions: [

        {

          expectedImprovement: 1,

        },

        {

          expectedImprovement: 6,

        },

        {

          expectedImprovement: 3,

        },

      ],

    });

  assert.equal(
    ranking[0]
      .expectedImprovement,
    6,
  );

});
test("applyOptimizedWeights updates weights", () => {

    const result =
        buildAutoWeightPackage({

            currentWeights: {

                rsi: 1,

            },

            learningResult: {

                metrics: {

                    rsi: {

                        winRate: 82,

                        averageReturnPercent: 8,

                        confidence: 1,

                        sampleSize: 100,

                    },

                },

            },

        });

    assert.ok(

        result.weights.rsi > 1

    );

});

test("snapshot comparison works",()=>{

    const diff=

        compareWeightSnapshots(

            {

                weights:{rsi:1}

            },

            {

                weights:{rsi:1.2}

            }

        );

    assert.equal(

        diff.length,

        1

    );

});

test("weight history append",()=>{

    const history=

        appendWeightHistory({

            history:[],

            entry:buildWeightHistoryEntry({

                weights:{rsi:1}

            })

        });

    assert.equal(

        history.length,

        1

    );

    assert.ok(

        latestWeightHistory(history)

    );

});


test("learning dashboard",()=>{

    const history=[

        {

            score:8,

            confidence:0.8,

            createdAt:new Date().toISOString()

        },

        {

            score:6,

            confidence:0.9,

            createdAt:new Date().toISOString()

        }

    ];

    const dash=

        buildLearningDashboard(history);

    assert.equal(

        dash.learning.trend,

        "UP"

    );

});


test("learning summary",()=>{

    const report=

        buildLearningReport([

            {

                score:7,

                confidence:0.9,

                createdAt:new Date().toISOString()

            }

        ]);

    assert.equal(

        report.summary.status,

        "Learning Improving"

    );

});


test("AI accuracy",()=>{

    const result=

        calculateAIAccuracy([

            {score:10},

            {score:5},

            {score:-2},

            {score:4}

        ]);

    assert.equal(

        result.accuracy,

        75

    );

});


test("AI reliability",()=>{

    const r=

        calculateReliability([

            {confidence:0.95},

            {confidence:0.90},

            {confidence:0.85}

        ]);

    assert.equal(

        r.grade,

        "S"

    );

});


test("AI performance index",()=>{

    const board=

        buildAIScoreBoard([

            {

                score:8,

                confidence:0.95,

                createdAt:new Date().toISOString()

            },

            {

                score:6,

                confidence:0.90,

                createdAt:new Date().toISOString()

            },

            {

                score:5,

                confidence:0.88,

                createdAt:new Date().toISOString()

            }

        ]);

    assert.ok(

        board.performance.index>0

    );

});


test("Evolution score",()=>{

    const report=

        buildEvolutionReport([

            {

                score:10,

                confidence:0.9,

                createdAt:new Date().toISOString()

            },

            {

                score:6,

                confidence:0.8,

                createdAt:new Date().toISOString()

            }

        ]);

    assert.equal(

        report.evolution.direction,

        "UP"

    );

});


test("Calibration report",()=>{

    const report=

        buildCalibrationReport([

            {

                score:12,

                confidence:0.95,

                createdAt:new Date().toISOString()

            },

            {

                score:10,

                confidence:0.90,

                createdAt:new Date().toISOString()

            }

        ]);

    assert.ok(

        report.calibration.calibration>0

    );

});


test("Adaptive weight engine",()=>{

    const report=

        buildAdaptiveLearningReport([

            {

                score:15,

                confidence:0.95,

                createdAt:new Date().toISOString()

            },

            {

                score:8,

                confidence:0.90,

                createdAt:new Date().toISOString()

            }

        ]);

    assert.ok(

        report.adaptive.multiplier>=1

    );

});


test("Backtest readiness",()=>{

    const history=[];

    for(let i=0;i<40;i++){

        history.push({

            score:10,

            confidence:0.92,

            createdAt:new Date().toISOString()

        });

    }

    const report=

        buildBacktestPackage(history);

    assert.equal(

        report.readiness.ready,

        true

    );

});


test("Optimization gate",()=>{

    const history=[];

    for(let i=0;i<50;i++){

        history.push({

            score:12,

            confidence:0.95,

            createdAt:new Date().toISOString()

        });

    }

    const result=

        buildOptimizationPackage(history);

    assert.ok(result.gate.performanceIndex > 0);

});



test("Market regime",()=>{

    const result=

        detectMarketRegime({

            trendScore:90,

            volatilityScore:20,

            momentumScore:85

        });

    assert.equal(

        result.regime,

        "BULL"

    );

});


test("Portfolio risk",()=>{

    const report=

        buildPortfolioAIReport({

            history:[],

            market:{},

            positions:[

                {

                    weight:50,

                    volatility:1.2

                },

                {

                    weight:30,

                    volatility:0.8

                }

            ]

        });

    assert.ok(

        report.portfolio.risk>0

    );

});


test("Position sizing",()=>{

    const result=

        buildTradingPlan({

            capital:100000,

            riskPercent:1,

            stopPercent:5

        });

    assert.ok(

        result.sizing.position>0

    );

});


test("Signal quality",()=>{

    const result=

        calculateSignalQuality({

            trend:90,

            momentum:85,

            volume:80,

            volatility:20

        });

    assert.equal(

        result.quality,

        "A"

    );

});


test("Trade decision engine",()=>{

    const decision=

        buildTradeDecision({

            signal:{score:90},

            learning:{score:80},

            market:{score:85},

            portfolio:{risk:10}

        });

    assert.ok(["BUY","STRONG BUY"].includes(decision.action));

});



test("Confidence calibration",()=>{

    const result=

        calibrateConfidence({

            prediction:90,

            accuracy:90,

            reliability:85,

            market:80

        });

    assert.equal(result.grade,"A");

});



test("Opportunity ranking",()=>{

    const ranking=

        rankOpportunities([

            {

                code:"A",

                signal:90,

                ai:85,

                market:80,

                volume:90

            },

            {

                code:"B",

                signal:60,

                ai:55,

                market:60,

                volume:50

            }

        ]);

    assert.equal(

        ranking[0].code,

        "A"

    );

});


test("Candidate filter",()=>{

    const result=

        buildTradeCandidates({

            candidates:[

                {

                    code:"AAA",

                    signal:90,

                    ai:90,

                    market:85,

                    volume:80

                },

                {

                    code:"BBB",

                    signal:30,

                    ai:40,

                    market:40,

                    volume:30

                }

            ],

            market:{

                trendScore:90,

                momentumScore:90,

                volatilityScore:20

            }

        });

    assert.equal(

        result.filtered.length,

        1

    );

});


test("Execution priority",()=>{

    const queue=

        assignExecutionPriority([

            {score:95},

            {score:82},

            {score:74}

        ]);

    assert.equal(

        queue[0].priority,

        "URGENT"

    );

    assert.equal(

        queue[1].priority,

        "HIGH"

    );

});


test("Risk reward optimizer",()=>{

    const list=

        optimizeExecutionCandidates([

            {

                entry:100,

                stop:95,

                target:120

            },

            {

                entry:100,

                stop:98,

                target:104

            }

        ]);

    assert.ok(

        list[0].rr.rr>

        list[1].rr.rr

    );

});



test("Portfolio optimizer",()=>{

    const result=

        optimizePortfolio([

            {

                code:"AAA",

                score:90

            },

            {

                code:"BBB",

                score:60

            }

        ]);

    assert.ok(

        result[0].allocation>

        result[1].allocation

    );

});


test("Capital allocation",()=>{

    const plan=

        buildCapitalPlan({

            capital:100000,

            candidates:[

                {

                    code:"AAA",

                    score:80

                },

                {

                    code:"BBB",

                    score:20

                }

            ]

        });

    assert.equal(

        plan.capitalPlan[0].capital,

        80000

    );

});


test(
  "Executable share allocation",
  () => {

    const result =
      calculateExecutableShares({

        capital: 50000,

        price: 400,

        lotSize: 100,

      });

    assert.equal(
      result.shares,
      100,
    );

    assert.equal(
      result.lots,
      1,
    );

    assert.equal(
      result.investedAmount,
      40000,
    );

    assert.equal(
      result.remainingCapital,
      10000,
    );

  },
);

test(
  "Executable capital plan",
  () => {

    const result =
      buildExecutableCapitalPlan({

        capital: 100000,

        candidates: [

          {

            code: "AAA",

            score: 80,

            price: 500,

          },

          {

            code: "BBB",

            score: 20,

            price: 100,

          },

        ],

        lotSize: 100,

      });

    assert.equal(
      result.executions[0].shares,
      100,
    );

    assert.ok(
      result.totalInvested <=
      100000,
    );

  },
);



test("Portfolio rebalance",()=>{

    const result=

        rebalancePortfolio({

            portfolio:[

                {

                    code:"AAA",

                    allocation:40

                },

                {

                    code:"BBB",

                    allocation:60

                }

            ],

            targetAllocation:[

                {

                    code:"AAA",

                    allocation:55

                },

                {

                    code:"BBB",

                    allocation:45

                }

            ]

        });

    assert.equal(

        result[0].action,

        "BUY"

    );

    assert.equal(

        result[1].action,

        "SELL"

    );

});



test("Performance metrics",()=>{

    const result=

        calculatePerformanceMetrics({

            trades:[

                {pnl:100},

                {pnl:-50},

                {pnl:200}

            ]

        });

    assert.equal(

        result.total,

        3

    );

    assert.equal(

        result.wins,

        2

    );

    assert.equal(

        result.winRate,

        66.67

    );

});



test(
  "Drawdown calculation",
  () => {

    const result =
      calculateDrawdown({

        initialEquity:
          100000,

        trades: [

          {
            pnl: 10000,
          },

          {
            pnl: -15000,
          },

          {
            pnl: 5000,
          },

        ],

      });

    assert.equal(
      result.finalEquity,
      100000,
    );

    assert.equal(
      result.maximumDrawdown,
      15000,
    );

    assert.ok(
      result.maximumDrawdownPercent >
      13,
    );

  },
);

test(
  "Profit factor calculation",
  () => {

    const result =
      calculateProfitFactor({

        trades: [

          {
            pnl: 100,
          },

          {
            pnl: 200,
          },

          {
            pnl: -100,
          },

        ],

      });

    assert.equal(
      result.grossProfit,
      300,
    );

    assert.equal(
      result.grossLoss,
      100,
    );

    assert.equal(
      result.profitFactor,
      3,
    );

  },
);

test(
  "Risk performance report",
  () => {

    const result =
      buildRiskPerformanceReport({

        trades: [

          {
            pnl: 100,
          },

          {
            pnl: -50,
          },

        ],

      });

    assert.equal(
      result.performance.total,
      2,
    );

    assert.ok(
      result.drawdown.curve.length >
      0,
    );

  },
);



test("Equity dashboard",()=>{

    const result=

        buildEquityDashboard({

            initialEquity:100000,

            trades:[

                {pnl:5000},

                {pnl:-2000},

                {pnl:3000}

            ]

        });

    assert.equal(

        result.equity.finalEquity,

        106000

    );

    assert.ok(

        result.equity.curve.length===3

    );

});



test("Monte Carlo simulation",()=>{

    const result=

        runMonteCarloSimulation({

            initialCapital:100000,

            simulations:20,

            trades:[

                {pnl:1000},

                {pnl:-500},

                {pnl:800}

            ]

        });

    assert.equal(

        result.simulations,

        20

    );

    assert.ok(

        result.bestCase>=

        result.worstCase

    );

});



test("Walk Forward Validation",()=>{

    const trades=[];

    for(

        let i=0;

        i<40;

        i++

    ){

        trades.push({

            pnl:

                i%2===0

                ?100

                :-50

        });

    }

    const result=

        runWalkForwardValidation({

            trades,

            windowSize:20

        });

    assert.equal(

        result.windows.length,

        2

    );

    assert.ok(

        result.averageWinRate>0

    );

});



test(
  "Candidate strategy improvement is approved",
  () => {

    const currentTrades =
      Array.from(

        {
          length: 20,
        },

        (
          _,
          index,
        ) => ({

          pnl:
            index % 2 === 0
              ? 100
              : -100,

        }),

      );

    const candidateTrades =
      Array.from(

        {
          length: 20,
        },

        (
          _,
          index,
        ) => ({

          pnl:
            index % 4 === 0
              ? -50
              : 150,

        }),

      );

    const result =
      compareStrategyPerformance({

        currentTrades,

        candidateTrades,

      });

    assert.equal(

      result.approved,

      true,

    );

    assert.ok(

      result.deltas.profit > 0,

    );

  },
);

test(
  "Worse candidate strategy is rejected",
  () => {

    const currentTrades =
      Array.from(

        {
          length: 20,
        },

        () => ({

          pnl: 100,

        }),

      );

    const candidateTrades =
      Array.from(

        {
          length: 20,
        },

        () => ({

          pnl: -100,

        }),

      );

    const result =
      compareStrategyPerformance({

        currentTrades,

        candidateTrades,

      });

    assert.equal(

      result.approved,

      false,

    );

    assert.ok(

      result.reasons.length > 0,

    );

  },
);

test(
  "Optimizer validation report includes weight changes",
  () => {

    const result =
      buildOptimizerValidationReport({

        currentTrades:
          Array.from(

            {
              length: 10,
            },

            () => ({

              pnl: 10,

            }),

          ),

        candidateTrades:
          Array.from(

            {
              length: 10,
            },

            () => ({

              pnl: 20,

            }),

          ),

        currentWeights: {

          rsi: 1,

        },

        candidateWeights: {

          rsi: 1.1,

        },

      });

    assert.equal(

      result.weightChanges.length,

      1,

    );

    assert.equal(

      result.weightChanges[0]
        .indicator,

      "rsi",

    );

  },
);


test("Weight version manager",()=>{

    const v1=

        createWeightVersion({

            weights:{

                rsi:1,

                macd:1

            },

            score:80

        });
    const v2=
        createWeightVersion({

            weights:{

                rsi:1.2,

                macd:0.9

            },

            score:90

        });

    const diff=

        compareWeightVersions(

            v1,

            v2

        );

    assert.equal(

        diff.length,

        2

    );

    assert.ok(

        diff[0].delta!==0

    );

});



test("Rollback manager",()=>{

    const v1=

        createWeightVersion({

            weights:{rsi:1}

        });
    const v2=
        createWeightVersion({

            weights:{rsi:1.2}

        });

    const history=

        buildVersionHistory({

            history:[v1],

            version:v2

        });

    const restored=

        rollbackWeightVersion({

            history,

            versionId:v1.id

        });

    assert.equal(

        restored.weights.rsi,

        1

    );

    const evalResult=

        evaluateWeightVersion(v2);

    assert.ok(

        evalResult.score>0

    );

});




test("Model snapshot",()=>{

    const s1=

        createModelSnapshot({

            weights:{rsi:1},

            metrics:{pf:2}

        });

    const s2=

        createModelSnapshot({

            weights:{rsi:1.2},

            metrics:{pf:3}

        });

    const diff=

        compareSnapshots(

            s1,

            s2

        );

    assert.equal(

        diff.length,

        1

    );

    const restored=

        restoreModelSnapshot({

            snapshot:s1

        });

    assert.equal(

        restored.weights.rsi,

        1

    );

});



test("Model registry",()=>{

    const s1=

        createModelSnapshot({

            weights:{rsi:1},

            metrics:{score:80}

        });

    const s2=

        createModelSnapshot({

            weights:{rsi:1.2},

            metrics:{score:90}

        });

    let registry=[];

    registry=

        registerModel({

            registry,

            snapshot:s1

        });

    registry=

        registerModel({

            registry,

            snapshot:s2

        });

    assert.equal(

        getLatestModel(

            registry

        ).id,

        s2.id

    );

    assert.equal(

        findModelById({

            registry,

            id:s1.id

        }).id,

        s1.id

    );

    registry=

        deleteModel({

            registry,

            id:s1.id

        });

    assert.equal(

        registry.length,

        1

    );

});



test(
  "Model promotion requires human approval",
  () => {

    const validationReport = {
      comparison: {
        approved: true,
        improvementScore: 4.2,
        reasons: [],
      },
    };

    const result =
      promoteModelCandidate({

        registry: [],

        currentWeights: {
          rsi: 1,
        },

        candidateWeights: {
          rsi: 1.1,
        },

        validationReport,

        humanApproval: false,

      });

    assert.equal(
      result.promoted,
      false,
    );

    assert.equal(
      result.registry.length,
      0,
    );

    assert.ok(
      result.gate.reasons.includes(
        "Human approval required",
      ),
    );

  },
);

test(
  "Validated model is promoted after human approval",
  () => {

    const validationReport = {
      comparison: {
        approved: true,
        improvementScore: 5.4,
        reasons: [],
      },
    };

    const result =
      promoteModelCandidate({

        registry: [],

        currentWeights: {
          rsi: 1,
        },

        candidateWeights: {
          rsi: 1.12,
        },

        validationReport,

        humanApproval: true,

      });

    assert.equal(
      result.promoted,
      true,
    );

    assert.equal(
      result.registry.length,
      1,
    );

    assert.equal(
      result.activeWeights.rsi,
      1.12,
    );

    assert.equal(
      result.activeModel.id,
      result.snapshot.id,
    );

  },
);

test(
  "Failed backtest cannot be promoted",
  () => {

    const result =
      promoteModelCandidate({

        registry: [],

        candidateWeights: {
          rsi: 1.2,
        },

        validationReport: {
          comparison: {
            approved: false,
            improvementScore: -1,
            reasons: [
              "Candidate profit decreased",
            ],
          },
        },

        humanApproval: true,

      });

    assert.equal(
      result.promoted,
      false,
    );

    assert.ok(
      result.gate.reasons.includes(
        "Candidate profit decreased",
      ),
    );

  },
);

test(
  "Rejected model does not change registry",
  () => {

    const existing =
      createModelSnapshot({

        weights: {
          rsi: 1,
        },

        metrics: {
          score: 80,
        },

      });

    const result =
      rejectModelCandidate({

        registry: [
          existing,
        ],

        reason:
          "Manual rejection",

      });

    assert.equal(
      result.rejected,
      true,
    );

    assert.equal(
      result.registry.length,
      1,
    );

    assert.equal(
      result.activeModel.id,
      existing.id,
    );

  },
);


test("Learning decision promote",()=>{

    const r=

        buildLearningDecisionReport({

            validationReport:{

                comparison:{

                    approved:true,

                    improvementScore:3,

                    reasons:[]

                }

            }

        });

    assert.equal(

        r.decision.action,

        "PROMOTE"

    );

});

test("Learning decision retrain",()=>{

    const r=

        buildLearningDecisionReport({

            validationReport:{

                comparison:{

                    approved:false,

                    improvementScore:-3,

                    reasons:["loss"]

                }

            }

        });

    assert.equal(

        r.decision.action,

        "RETRAIN"

    );

});


test("Learning cycle promote",()=>{

    const cycle=

        executeLearningCycle({

            registry:[],

            validationReport:{

                comparison:{

                    approved:true,

                    improvementScore:5,

                    reasons:[]

                }

            },

            currentWeights:{rsi:1},

            candidateWeights:{rsi:1.1},

            humanApproval:true

        });

    assert.equal(

        cycle.result.promoted,

        true

    );

});

test("Learning cycle hold",()=>{

    const cycle=

        executeLearningCycle({

            registry:[],

            validationReport:{

                comparison:{

                    approved:false,

                    improvementScore:0,

                    reasons:[]

                }

            }

        });

    const summary=

        summarizeLearningCycle(cycle);

    assert.equal(

        summary.action,

        "HOLD"

    );

});


test(
  "Learning audit entry is created",
  () => {

    const cycle =
      executeLearningCycle({

        registry: [],

        validationReport: {

          comparison: {

            approved: true,

            improvementScore: 4.5,

            reasons: [],

          },

        },

        currentWeights: {

          rsi: 1,

        },

        candidateWeights: {

          rsi: 1.1,

        },

        humanApproval: true,

      });

    const entry =
      createLearningAuditEntry({

        cycle,

        source: "test",

      });

    assert.equal(
      entry.promoted,
      true,
    );

    assert.equal(
      entry.action,
      "PROMOTE",
    );

    assert.equal(
      entry.improvementScore,
      4.5,
    );

  },
);

test(
  "Learning audit history avoids duplicate ids",
  () => {

    const entry = {

      id: "same-id",

      createdAt:
        "2026-08-02T00:00:00.000Z",

      action: "HOLD",

      promoted: false,

      retraining: false,

      improvementScore: 0,

    };

    const history =
      appendLearningAuditHistory({

        history: [
          entry,
        ],

        entry,

      });

    assert.equal(
      history.length,
      1,
    );

  },
);

test(
  "Learning audit summary calculates promotion rate",
  () => {

    const result =
      summarizeLearningAuditHistory([

        {

          id: "a",

          action: "PROMOTE",

          promoted: true,

          retraining: false,

          improvementScore: 5,

        },

        {

          id: "b",

          action: "HOLD",

          promoted: false,

          retraining: false,

          improvementScore: 0,

        },

      ]);

    assert.equal(
      result.totalRuns,
      2,
    );

    assert.equal(
      result.promotionRate,
      50,
    );

    assert.equal(
      result.averageImprovement,
      2.5,
    );

  },
);


test("Weight health monitor",()=>{

    const report=

        evaluateWeightHealth({

            weights:{

                rsi:1,

                macd:1.5,

                adx:-0.2

            }

        });

    assert.equal(

        report.healthy,

        false

    );

    assert.ok(

        report.warnings.length>=2

    );

});


test("Normalize weights",()=>{

    const result=

        normalizeWeights({

            weights:{

                rsi:2.5,

                macd:0,

                adx:1

            }

        });

    assert.ok(

        result.rsi<=2

    );

    assert.ok(

        result.macd>=0.1

    );

});


test("Self evolution plan",()=>{

    const currentTrades=

        Array.from(

            {length:20},

            (_,index)=>({

                pnl:

                    index%2===0

                    ?100

                    :-100

            })

        );

    const candidateTrades=

        Array.from(

            {length:20},

            (_,index)=>({

                pnl:

                    index%4===0

                    ?-50

                    :150

            })

        );

    const learningResult={

        metrics:{

            rsi:{

                winRate:80,

                averageReturnPercent:5,

                confidence:1,

                sampleSize:50

            }

        }

    };

    const plan=

        buildSelfEvolutionPlan({

            currentWeights:{

                rsi:1

            },

            learningResult,

            currentTrades,

            candidateTrades,

            registry:[],

            humanApproval:true

        });

    const summary=

        summarizeSelfEvolutionPlan(

            plan

        );

    assert.equal(

        summary.approvedByBacktest,

        true

    );

    assert.equal(

        summary.weightHealth,

        true

    );

    assert.ok(

        summary.changedIndicators>=1

    );

});


test("Continuous learning scheduler",()=>{

    const schedule=

        buildLearningSchedule({

            intervalHours:1,

            lastRunAt:

                "2020-01-01T00:00:00.000Z"

        });

    assert.equal(

        shouldRunLearning({

            schedule

        }),

        true

    );

});

