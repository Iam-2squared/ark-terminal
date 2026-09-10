import assert from 'node:assert/strict';
import test from 'node:test';
import {
  PHASE57_SELECTOR_V3_FREEZE,
  PHASE57_SELECTOR_V3_SAFETY,
  scorePhase57SelectorV3CrossSection,
  selectPhase57SelectorV3,
} from '../daytrade/phase57-selector-v3.js';

const START=Date.parse('2026-09-04T00:00:00.000Z');
const iso=value=>new Date(value).toISOString();

function bars({base=100,step=0.2,volume=100000,count=16,sessionDate='2026-09-04'}={}){
  const out=[];
  let previous=base;
  for(let index=0;index<count;index+=1){
    const open=previous;
    const close=base+step*(index+1);
    const pad=Math.max(0.05,Math.abs(step)*0.5);
    out.push({
      timestamp:iso(START+index*5*60_000),
      availableAt:iso(START+(index+1)*5*60_000),
      sessionDate,open,high:Math.max(open,close)+pad,low:Math.min(open,close)-pad,close,
      volume:volume+index*100,
    });
    previous=close;
  }
  return out;
}

function entry(symbol,{sector='TECH',base=100,step=0.2,volume=100000,extraBars=[]}={}){
  return {symbol,sector,market:'PRIME',bars:[...bars({base,step,volume}),...extraBars]};
}

const cutoff=iso(START+12*5*60_000);

test('V3 uses only bars causally available by the feature cutoff',()=>{
  const base=entry('1001.T');
  const future={
    timestamp:iso(START+16*5*60_000),availableAt:iso(START+17*5*60_000),sessionDate:'2026-09-04',
    open:103.2,high:1000,low:1,close:900,volume:999999999,
  };
  const left=scorePhase57SelectorV3CrossSection({featureCutoff:cutoff,entries:[base]});
  const right=scorePhase57SelectorV3CrossSection({featureCutoff:cutoff,entries:[entry('1001.T',{extraBars:[future]})]});
  assert.deepEqual(left.ranked,right.ranked);
});

test('missing bar data fails closed instead of being changed to zero',()=>{
  const broken=entry('1001.T');
  delete broken.bars[4].volume;
  assert.throws(
    ()=>scorePhase57SelectorV3CrossSection({featureCutoff:cutoff,entries:[broken]}),
    /missing finite volume; missing values cannot be zero-filled/,
  );
});

test('conflicting duplicate bar availability fails closed',()=>{
  const broken=entry('1001.T');
  broken.bars.push({...broken.bars[3],close:broken.bars[3].close+1,high:broken.bars[3].high+1});
  assert.throws(
    ()=>scorePhase57SelectorV3CrossSection({featureCutoff:cutoff,entries:[broken]}),
    /conflicting duplicate availableAt/,
  );
});

test('V3 has no low-price or case-specific rejection rule',()=>{
  const entries=[
    entry('8918.T',{sector:'OTHER',base:10,step:0.05,volume:20_000_000}),
    ...Array.from({length:12},(_,index)=>entry(`${2000+index}.T`,{
      sector:`S${index%4}`,base:200+index,step:0.05+(index%3)*0.01,volume:50_000+index*1000,
    })),
  ];
  const scored=scorePhase57SelectorV3CrossSection({featureCutoff:cutoff,entries});
  const cheap=scored.ranked.find(row=>row.symbol==='8918.T');
  assert.ok(cheap);
  assert.equal(cheap.currentPrice<100,true);
  assert.equal(scored.rejected.some(row=>row.symbol==='8918.T'),false);
});

test('momentum and extension/headroom are separate components',()=>{
  const scored=scorePhase57SelectorV3CrossSection({
    featureCutoff:cutoff,
    entries:[
      entry('1001.T',{sector:'TECH',step:1.2,volume:500000}),
      entry('1002.T',{sector:'TECH',step:0.2,volume:500000}),
      entry('1003.T',{sector:'TECH',step:-0.2,volume:500000}),
    ],
  });
  const extended=scored.ranked.find(row=>row.symbol==='1001.T');
  assert.ok(extended.momentum>=0);
  assert.ok(extended.remainingHeadroom<1);
  assert.ok(extended.components.extensionPenalty>0);
  assert.notEqual(extended.momentum,extended.remainingHeadroom);
});

test('absolute threshold allows dynamic N and never fills to 30',()=>{
  const entries=Array.from({length:40},(_,index)=>entry(`${3000+index}.T`,{
    sector:`S${index%8}`,base:100+index,step:(index%5-2)*0.02,volume:10000+index*100,
  }));
  const selected=selectPhase57SelectorV3({featureCutoff:cutoff,entries,threshold:0.7});
  assert.ok(selected.selectedCount<30);
  assert.equal(selected.fixedCountFillUsed,false);
  const abstain=selectPhase57SelectorV3({featureCutoff:cutoff,entries,threshold:null});
  assert.equal(abstain.selectedCount,0);
  assert.match(abstain.status,/ABSTAIN/);
});

test('sector cap is applied after absolute quality gating without persistence',()=>{
  const entries=Array.from({length:12},(_,index)=>entry(`${4000+index}.T`,{
    sector:'ONE_SECTOR',base:100+index,step:0.3+index*0.02,volume:1_000_000+index*10000,
  }));
  const selected=selectPhase57SelectorV3({featureCutoff:cutoff,entries,threshold:0.45});
  assert.ok(selected.selectedCount<=PHASE57_SELECTOR_V3_FREEZE.selection.maximumSelectedPerSector);
  assert.equal(selected.persistenceUsed,false);
});

test('all execution, write, promotion and transmission surfaces remain false',()=>{
  for(const key of [
    'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
    'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted',
  ])assert.equal(PHASE57_SELECTOR_V3_SAFETY[key],false,key);
  assert.equal(PHASE57_SELECTOR_V3_FREEZE.scope.laneYMainChangeAllowed,false);
  assert.equal(PHASE57_SELECTOR_V3_FREEZE.scope.v1ChangeAllowed,false);
  assert.equal(PHASE57_SELECTOR_V3_FREEZE.scope.v2ChangeAllowed,false);
});

