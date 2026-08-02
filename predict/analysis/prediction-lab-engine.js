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
