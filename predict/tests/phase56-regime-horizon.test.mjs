import test from'node:test';import assert from'node:assert/strict';import{classifyRegime,regimeSignalPolicy,PHASE56_REGIME_SAFETY}from'../chart/phase56-regime-horizon.js';
const bars=(step=.5,n=80)=>Array.from({length:n},(_,i)=>({close:100+i*step,volume:1000+i}));
test('classifies trend and blocks countertrend signal',()=>{const b=bars();assert.equal(classifyRegime(b).regime,'TREND_UP');assert.equal(regimeSignalPolicy({bars:b,horizon:1,baseSignal:-1}).allow,false);});
test('allows aligned trend signal',()=>{assert.equal(regimeSignalPolicy({bars:bars(),horizon:1,baseSignal:1}).allow,true);});
test('remains research only',()=>{assert.equal(PHASE56_REGIME_SAFETY.executionAllowed,false);assert.equal(PHASE56_REGIME_SAFETY.brokerWriteAllowed,false);});
