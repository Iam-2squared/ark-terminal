import assert from 'node:assert/strict';
import {P23_20_PROTECT_POLICY,estimateProtectionEvidence,deriveProtectionStop,stopFill} from '../daytrade/phase57-probabilistic-profit-protection.js';

assert.equal(P23_20_PROTECT_POLICY.thresholdSearchAllowed,false);
assert.equal(P23_20_PROTECT_POLICY.outcomeTuningAllowed,false);
const state={currentReturnPct:0.4,bestReturnPct:0.8,givebackPctPoints:0.4,atrPct:0.2,momentumPct:-0.1,bodyPressure:-0.5,directionalRangePos:0.7};
const pool=Array.from({length:25},(_,i)=>({setup:'BREAKOUT_CONTINUATION_UP',direction:'UP',fullyRealizedAt:`2026-01-${String(i%9+1).padStart(2,'0')}T01:00:00.000Z`,state:{...state,currentReturnPct:0.4+i*0.001},nextDirectionalReturnPct:i<8?-0.3:0.2}));
const q={setup:'BREAKOUT_CONTINUATION_UP',direction:'UP',timestamp:'2026-02-01T01:00:00.000Z',state};
const ev=estimateProtectionEvidence(q,pool);
assert.equal(ev.ready,true);
assert.equal(ev.neighborCount,25);
assert.ok(ev.q10DirectionalReturnPct<0);
const p=deriveProtectionStop({entryPrice:100,currentPrice:101,direction:'UP',currentGrossReturnPct:1,priorStop:null,evidence:ev});
assert.equal(p.state,'PROTECT');
assert.ok(p.stop>=100.05&&p.stop<=101);
const p2=deriveProtectionStop({entryPrice:100,currentPrice:101.2,direction:'UP',currentGrossReturnPct:1.2,priorStop:p.stop,evidence:ev});
assert.ok(p2.stop>=p.stop);
assert.equal(stopFill({open:101,high:101.2,low:p.stop-0.01,close:101},p.stop,'UP'),p.stop);
console.log('P23.20 causal profit protection tests passed');
