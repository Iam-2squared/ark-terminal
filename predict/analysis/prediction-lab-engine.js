import {
createPredictionMetadata
} from "./prediction-metadata.js";

import {
buildAnalysisCore
} from "./analysis-core.js";

import {
buildPerformanceMonitor
} from "./performance-monitor.js";

import {
buildConfidenceReport
} from "./confidence-calibration.js";

import {
buildWalkForwardReport
} from "./walk-forward-engine.js";

export function buildPredictionLabEngine({

state={},
macroInput={},
marketInput={},
portfolioPlan={},
history=[]

}={}){

const analysis=

buildAnalysisCore({

state,
macroInput,
marketInput,
portfolioPlan

});

const performance=

buildPerformanceMonitor({

history

});

const confidence=

buildConfidenceReport({

confidence:
analysis.dashboard.confidence,

performance:
performance.report,

sampleSize:
performance.report.total

});

const predictionMetadata=

createPredictionMetadata({

symbol:
state.symbol ??
state.ticker ??
state.code,

predictedAt:
new Date().toISOString(),

timeframe:
state.period ??
state.prediction?.period ??
5,

direction:
analysis.dashboard.action,

confidence:
confidence.confidence,

score:
analysis.dashboard.score,

entryPrice:
state.price ??
state.currentPrice ??
state.quote?.price,

targetPrice:
state.targetPrice ??
state.prediction?.targetPrice,

stopPrice:
state.stopPrice ??
state.prediction?.stopPrice,

marketRegime:
state.regime?.regime ??
state.market?.regime,

modelVersion:
"prediction-lab-v2",

dataQualityScore:
state.analysis?.dataQualityScore,

source:
"prediction-lab-engine"

});

const walkForward=

buildWalkForwardReport({

history

});

return{

version:

"prediction-lab-v2",

generatedAt:

new Date().toISOString(),

analysis,

performance,

confidence,

walkForward,

dashboard:{

action:
analysis.dashboard.action,

score:
analysis.dashboard.score,

confidence:
confidence.confidence,

grade:
performance.grade,

walkForward:
walkForward.stable

}

};

}

export function buildPredictionSummary({

engine

}){

return{

title:

"Prediction Lab AI",

action:

engine.dashboard.action,

score:

engine.dashboard.score,

confidence:

engine.dashboard.confidence,

grade:

engine.dashboard.grade

};

}
