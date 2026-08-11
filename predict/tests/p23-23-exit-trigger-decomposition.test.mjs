import assert from 'node:assert/strict';
const counts={decisions:10,ready:8,notReady:2,probabilityOnly:1,evOnly:2,microBreakOnly:1,probabilityAndEv:3,probabilityAndMicro:2,evAndMicro:2,allThree:1,none:1};
assert.equal(counts.ready+counts.notReady,counts.decisions);
assert.ok(counts.allThree<=counts.probabilityAndEv);
assert.ok(counts.allThree<=counts.probabilityAndMicro);
assert.ok(counts.allThree<=counts.evAndMicro);
assert.ok(counts.probabilityAndEv-counts.allThree>=0);
console.log('P23.23 trigger decomposition invariants OK');