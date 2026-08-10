import assert from 'node:assert/strict';
import { scoreHumanStyleSetupQuality, PHASE57_P23_10D_QUALITY_POLICY } from '../daytrade/phase57-chart-setup-quality.js';

const tf=(regime,quality=0.8)=>({status:'CHART_PERCEPTION_READY',structure:{regime},trendQuality:{score:quality}});
const perception={timeframes:{
  '5m':{...tf('UPTREND',0.9),currentCandle:{direction:'UP',bodyStrength:0.8},volume:{ratio:1.8},volatility:{state:'EXPANDING'},breakout:{state:'BREAKOUT_UP'},phase:{phase:'UPTREND_IMPULSE'}},
  '15m':tf('UPTREND',0.8),'60m':tf('UPTREND',0.7),'1d':tf('UPTREND',0.6),
}};
const high=scoreHumanStyleSetupQuality(perception,{setup:'BREAKOUT_CONTINUATION_UP',directionSign:1});
assert.ok(high.score>0.7 && high.score<=1);
assert.equal(high.outcomeUsed,false);
assert.equal(high.futureBarsUsed,false);
const hostile={timeframes:{...perception.timeframes,'15m':tf('DOWNTREND',0.8),'60m':tf('DOWNTREND',0.8),'1d':tf('DOWNTREND',0.8)}};
const low=scoreHumanStyleSetupQuality(hostile,{setup:'BREAKOUT_CONTINUATION_UP',directionSign:1});
assert.ok(low.score<high.score);
assert.equal(PHASE57_P23_10D_QUALITY_POLICY.outcomeTuned,false);
assert.equal(PHASE57_P23_10D_QUALITY_POLICY.futureOutcomeUsed,false);
console.log('P23.10D setup quality tests passed');
