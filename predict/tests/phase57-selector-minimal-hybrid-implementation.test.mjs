import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import test from 'node:test';

import {
  PHASE57_MINIMAL_HYBRID_MODEL_FEATURES,
  describePhase57MinimalHybridFeatures,
  predictPhase57MinimalHybridTargets,
  trainPhase57MinimalHybridModel,
} from '../daytrade/phase57-selector-minimal-hybrid-model.js';
import {
  extractPhase57MinimalHybridFeatures,
  runPhase57MinimalHybrid,
} from '../daytrade/phase57-selector-minimal-hybrid.js';
import {buildPhase57MinimalHybridTargets} from '../daytrade/phase57-selector-minimal-hybrid-targets.js';

const FEATURE_CUTOFF='2025-01-06T01:30:00.000Z';
const TRAINING_FEATURES=Object.freeze([
  'turnoverRank','relativeActivity','maSlopeAtr','vwapSlopeAtr',
  'pathEfficiency','reversalFrequency','extensionPersistenceInteraction','extensionReversalInteraction',
]);

function sha256(buffer){return createHash('sha256').update(buffer).digest('hex');}

function bar({timestamp,open,close,volume}){
  const timestampMs=Date.parse(timestamp);
  const spread=Math.max(0.08,Math.abs(close-open)*0.25);
  return {
    timestamp,
    availableAt:new Date(timestampMs+5*60_000).toISOString(),
    sessionDate:'2025-01-06',
    open:Number(open.toFixed(4)),high:Number((Math.max(open,close)+spread).toFixed(4)),
    low:Number((Math.min(open,close)-spread).toFixed(4)),close:Number(close.toFixed(4)),
    volume,turnover:Number((close*volume).toFixed(2)),
  };
}

function makeBars(symbolIndex,{future=false}={}){
  const pattern=symbolIndex%4;
  let price=80+symbolIndex*2;
  const rows=[];
  for(let index=0;index<18;index+=1){
    const timestamp=new Date(Date.parse('2025-01-06T00:00:00.000Z')+index*5*60_000).toISOString();
    const open=price;
    const step=pattern===0?0.34:pattern===1?(index%2?0.06:0.52):pattern===2?-0.28:(index%2?-0.32:0.38);
    price=Math.max(10,price+step);
    const activityBoost=index>=12?(pattern===0?1.75:pattern===1?1.3:pattern===2?1.55:0.85):1;
    rows.push(bar({timestamp,open,close:price,volume:Math.round((9000+symbolIndex*850+index*110)*activityBoost)}));
  }
  if(future){
    rows.push(bar({timestamp:'2025-01-06T02:00:00.000Z',open:price,close:price*1.35,volume:9_999_999}));
  }
  return rows;
}

function makeEntries({future=false}={}){
  return Array.from({length:24},(_,index)=>({
    symbol:`T${String(index+1).padStart(3,'0')}`,
    sector:`S${Math.floor(index/4)+1}`,
    market:'PRIME',
    bars:makeBars(index,{future}),
  }));
}

function makeTrainingSamples(){
  return Array.from({length:32},(_,index)=>{
    const x=(index-15.5)/15.5;
    const persistence=(index%7)/6;
    const reversal=((index*3)%11)/10;
    const extension=((index*5)%13)/12;
    const features={
      turnoverRank:index/31,
      relativeActivity:0.65+(index%9)*0.19,
      maSlopeAtr:x*1.4,
      vwapSlopeAtr:x*1.05+(index%3-1)*0.08,
      pathEfficiency:persistence,
      reversalFrequency:reversal,
      extensionPersistenceInteraction:extension*persistence,
      extensionReversalInteraction:extension*reversal,
    };
    const quality=0.0032+0.004*persistence-0.0024*reversal+0.002*features.extensionPersistenceInteraction-0.0015*features.extensionReversalInteraction;
    return {
      sessionDate:'2025-01-02',features,
      targets:{
        upExcursion:Math.max(0.0002,quality+0.0025*x),
        downExcursion:Math.max(0.0002,quality-0.0025*x),
        twoSidedOpportunityUsedAsTrainingTarget:false,
      },
    };
  });
}

function trainModel(overrides={}){
  return trainPhase57MinimalHybridModel({
    samples:makeTrainingSamples(),featureNames:TRAINING_FEATURES,ridgeLambda:0.2,
    trainingContext:{mode:'SYNTHETIC_FIXTURE_ONLY'},
    selectionPolicy:{
      source:'SYNTHETIC_FIXTURE_ONLY',maximumSelected:10,
      minimumRemainingOpportunityScore:0.08,opportunityScale:0.01,
      maximumAbsoluteSoftAdjustment:0.2,
      ...overrides,
    },
  });
}

test('Phase A original bytes remain frozen and v1.1 amendment is separately hashable',()=>{
  const original=fs.readFileSync(new URL('../research/phase57-selector-minimal-hybrid-phase-a.json',import.meta.url));
  assert.equal(sha256(original),'7ca1b53a25ea756785ed0320e3887fb78ec6be557df53f0840638aeba14dafda');
  const amendment=fs.readFileSync(new URL('../research/phase57-selector-minimal-hybrid-phase-a-amendment-v1.1.json',import.meta.url));
  const recorded=fs.readFileSync(new URL('../research/phase57-selector-minimal-hybrid-phase-a-amendment-v1.1.sha256',import.meta.url),'utf8').trim().split(/\s+/)[0];
  assert.equal(sha256(amendment),recorded);
});

test('target builder separates Up/Down and excludes cutoff and cross-session bars',()=>{
  const futureBars=[
    {availableAt:FEATURE_CUTOFF,sessionDate:'2025-01-06',high:999,low:1,close:100},
    ...Array.from({length:12},(_,index)=>({
      availableAt:new Date(Date.parse(FEATURE_CUTOFF)+(index+1)*5*60_000).toISOString(),
      sessionDate:'2025-01-06',high:101+index*0.2,low:99-index*0.1,close:100+(index%2?0.2:-0.1),
    })),
    {availableAt:'2025-01-07T00:05:00.000Z',sessionDate:'2025-01-07',high:500,low:1,close:250},
  ];
  const result=buildPhase57MinimalHybridTargets({featureCutoff:FEATURE_CUTOFF,anchorPrice:100,sessionDate:'2025-01-06',futureBars});
  assert.equal(result.horizons[12].status,'TARGET_READY');
  assert.equal(result.horizons[12].upExcursion,0.032);
  assert.equal(result.horizons[12].downExcursion,0.021);
  assert.equal(result.methodology.twoSidedPrimaryTrainingTarget,false);
});

test('multi-target model is deterministic, finite, and rejects missing or direct extension input',()=>{
  const left=trainModel(),right=trainModel();
  assert.deepEqual(left,right);
  assert.notDeepEqual(left.upCoefficients,left.downCoefficients);
  const inference=predictPhase57MinimalHybridTargets({model:left,features:makeTrainingSamples()[3].features});
  assert.ok(Number.isFinite(inference.expectedUpExcursion));
  assert.ok(Number.isFinite(inference.expectedDownExcursion));
  assert.throws(()=>predictPhase57MinimalHybridTargets({model:left,features:{}}),/missing cannot become zero/);
  assert.throws(()=>trainPhase57MinimalHybridModel({
    samples:makeTrainingSamples(),featureNames:['extensionAtr'],ridgeLambda:0.2,
    trainingContext:{mode:'SYNTHETIC_FIXTURE_ONLY'},
    selectionPolicy:{source:'SYNTHETIC_FIXTURE_ONLY',maximumSelected:2,minimumRemainingOpportunityScore:0.1,opportunityScale:0.01,maximumAbsoluteSoftAdjustment:0.1},
  }),/outside the Minimal set|direct extension/);
});

test('5m feature pipeline is causal and uses conditional extension only',()=>{
  const base=extractPhase57MinimalHybridFeatures({featureCutoff:FEATURE_CUTOFF,entries:makeEntries()});
  const withFuture=extractPhase57MinimalHybridFeatures({featureCutoff:FEATURE_CUTOFF,entries:makeEntries({future:true})});
  assert.deepEqual(base,withFuture);
  assert.equal(base.status,'MINIMAL_HYBRID_5M_FEATURES_READY');
  assert.equal(base.rankedFeatures.length,24);
  assert.equal(base.methodology.rawExtensionUsedAsDirectPenalty,false);
  assert.equal(base.methodology.conditionalExtensionInteractionsOnly,true);
  assert.equal(PHASE57_MINIMAL_HYBRID_MODEL_FEATURES.includes('extensionAtr'),false);
});

test('lunch/session segmentation is atomic and bars are not bridged',()=>{
  const am=makeBars(0).slice(0,9);
  let price=100;
  const pm=Array.from({length:3},(_,index)=>{
    const open=price;price+=0.2;
    return bar({timestamp:new Date(Date.parse('2025-01-06T03:30:00.000Z')+index*5*60_000).toISOString(),open,close:price,volume:12000});
  });
  const result=extractPhase57MinimalHybridFeatures({featureCutoff:'2025-01-06T03:45:00.000Z',entries:[{symbol:'LUNCH',sector:'S1',bars:[...am,...pm]}]});
  assert.equal(result.status,'MINIMAL_HYBRID_NO_ELIGIBLE_FEATURE_ROWS');
  assert.equal(result.rejected[0].reason,'INSUFFICIENT_CURRENT_SEGMENT_5M_BARS');
});

test('end-to-end Hybrid preserves V1 recall then performs bounded soft ranking and Dynamic N',()=>{
  const model=trainModel();
  const args={featureCutoff:FEATURE_CUTOFF,entries:makeEntries(),model,baselineDiagnostics:{v3SelectedSymbols:['NOT_IN_V1']}};
  const first=runPhase57MinimalHybrid(args),second=runPhase57MinimalHybrid(args);
  assert.deepEqual(first,second);
  assert.equal(first.status,'MINIMAL_HYBRID_SELECTION_READY');
  assert.ok(first.v1CandidateCount>first.dynamicN);
  assert.ok(first.dynamicN>0&&first.dynamicN<=10);
  assert.ok(first.ranked.every(row=>Number.isFinite(row.hybridScore)&&Math.abs(row.softAdjustment)<=0.2));
  assert.ok(first.selected.every(row=>row.stage2.remainingOpportunityScore>=0.08));
  assert.equal(first.evidence.hybridAllFromV1BroadRecall,true);
  assert.equal(first.evidence.hybridRankChangedFromV1,true);
  assert.equal(first.evidence.hybridIdenticalToV1,false);
  assert.equal(first.evidence.hybridExtinct,false);
  assert.equal(first.evidence.baselineDiagnosticsUsedForHybrid,false);
  assert.equal(first.methodology.v3MembershipRequired,false);
  assert.equal(first.methodology.directExtensionPenaltyUsed,false);
  assert.equal(first.methodology.entryDirectionUsed,false);
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted'])assert.equal(first.safety[key],false,key);
});

test('future bars do not alter inference and structural responsibility violations fail closed',()=>{
  const model=trainModel();
  const base=runPhase57MinimalHybrid({featureCutoff:FEATURE_CUTOFF,entries:makeEntries(),model});
  const withFuture=runPhase57MinimalHybrid({featureCutoff:FEATURE_CUTOFF,entries:makeEntries({future:true}),model});
  assert.deepEqual(base,withFuture);
  const poisoned=makeEntries();poisoned[0]={...poisoned[0],entryDirection:'BUY'};
  assert.throws(()=>runPhase57MinimalHybrid({featureCutoff:FEATURE_CUTOFF,entries:poisoned,model}),/forbidden entryDirection/);
});

test('Development-configured quality threshold can soft-ABSTAIN without changing Stage 1',()=>{
  const model=trainModel({minimumRemainingOpportunityScore:0.999,opportunityScale:1000});
  const result=runPhase57MinimalHybrid({featureCutoff:FEATURE_CUTOFF,entries:makeEntries(),model});
  assert.equal(result.status,'MINIMAL_HYBRID_SOFT_ABSTAIN');
  assert.ok(result.v1CandidateCount>0);
  assert.equal(result.dynamicN,0);
  assert.equal(result.evidence.hybridExtinct,true);
});

test('feature diagnostics expose Development-only screening inputs without selecting features',()=>{
  const result=describePhase57MinimalHybridFeatures(makeTrainingSamples());
  assert.equal(result.developmentSelectionApplied,false);
  for(const name of PHASE57_MINIMAL_HYBRID_MODEL_FEATURES){
    assert.ok(name in result.byFeature);
    assert.ok(result.byFeature[name].missingRate>=0&&result.byFeature[name].missingRate<=1);
  }
});
