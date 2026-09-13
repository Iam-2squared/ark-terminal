import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {runPhase57MinimalHybrid} from '../../predict/daytrade/phase57-selector-minimal-hybrid.js';
import {scoreP25ExitV2StateConditioned,validateP25ExitV2AnalogPool} from '../../predict/daytrade/phase57-p25-exit-v2-state-conditioned.js';
import {decideP25ExitV4,P25_EXIT_V4_POLICY_SHA256} from '../../predict/daytrade/phase57-p25-exit-v4-structural-risk.js';
import {buildDirectionFeatures,selectionSchedule,CONTRACT as ENTRY_CONTRACT,SAFETY as ENTRY_SAFETY} from './phase57-minimal-stateful-entry.mjs';
import {score} from '../phase57-capital-allocation-v3-phase-a.mjs';
import {buildEntryTimeOpportunity} from './phase57-capital-allocation-v3-entrytime.mjs';
import {Bar5Manager,MODEL,digest,exposedDate,hash,instant,iso} from './phase57-offline-parity.mjs';
import {createOfflineShadowLedger} from './phase57-offline-shadow-ledger.mjs';

export const FROZEN_MAIN_SCHEMA='ARK_PHASE57_FROZEN_MAIN_POINT_V1';
export const FROZEN_MAIN_POLICY=Object.freeze({
  selector:'FROZEN_MINIMAL_HYBRID_V1',entry:'MSH_ENTRY_V1',allocation:'V3_B_RISK',capacity:'MAX_3',
  exit:'EXIT_V5_DYNAMIC_RECLAIM_BAR_5',underlyingExit:'EXIT_V4_STRUCTURAL_RISK',
  mode:'LOCAL_SHADOW_RESEARCH_ONLY',executionAllowed:false,brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,
  paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,
});
const SELECTOR_MODEL_DIGEST='444e296d31b0e59263f268706b4c8a7c7e9e59d6f7c9547e9f90342a24040fc2';
const SELECTOR_FREEZE_SHA='a744d599e430d23efe4dea6600e418d3410d8a18df5055b35e1cc71432bf64da';
const SELECTOR_MODEL_FILE_SHA='b30d5386884678dcab3660d8caf07d9b3031bc9d5c16605ea10fdb6556d4bca5';
const SELECTOR_FREEZE_FILE_SHA='25ee8e34509825ce9647a9170b0bf529467f7a23e353bcbdd74d7fa4ebb5b967';
const forbidden=/^(labels?|targets?|outcomes?|future.*|mfe.*|mae.*|realized.*|netReturn.*|grossReturn.*|orders?|account.*|broker.*)$/i;
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const memberHash=rows=>hash([...rows].map(x=>x.symbol).sort());

function rejectForbidden(value){
  if(!value||typeof value!=='object')return;
  for(const [key,child] of Object.entries(value)){if(forbidden.test(key))throw Error(`FORBIDDEN_POINT_FIELD:${key}`);rejectForbidden(child);}
}
function canonicalBar(bar,symbol,at,date,index){
  assert.ok(bar&&typeof bar==='object',`INVALID_BAR:${symbol}:${index}`);
  const timestamp=iso(instant(bar.timestamp)),availableAt=iso(instant(bar.availableAt));
  assert.equal(new Date(instant(timestamp)+32400000).toISOString().slice(0,10),date,'CROSS_SESSION_BAR');
  assert.ok(instant(timestamp)%300000===0&&instant(timestamp)+300000<=instant(at),'FORMING_OR_OFF_GRID_BAR');
  const local=iso(instant(timestamp)+32400000),minute=Number(local.slice(11,13))*60+Number(local.slice(14,16));
  assert.ok((minute>=540&&minute<690)||(minute>=750&&minute<930),'BAR_OUTSIDE_REGULAR_SESSION');
  assert.ok(instant(availableAt)>=instant(timestamp)+300000&&instant(availableAt)<=instant(at),'NON_PIT_BAR');
  for(const key of ['open','high','low','close','volume'])assert.ok(finite(bar[key]),`INVALID_${key.toUpperCase()}`);
  assert.ok(Math.min(bar.open,bar.low,bar.close)>0&&bar.high>=Math.max(bar.open,bar.low,bar.close)&&bar.low<=Math.min(bar.open,bar.close)&&bar.volume>=0,'INVALID_OHLCV');
  return {timestamp,availableAt,sessionDate:date,open:bar.open,high:bar.high,low:bar.low,close:bar.close,volume:bar.volume,...(finite(bar.turnover)?{turnover:bar.turnover}:{})};
}
function validatePoint(input){
  rejectForbidden(input);
  assert.equal(input?.schemaId,FROZEN_MAIN_SCHEMA,'POINT_SCHEMA_MISMATCH');
  assert.ok(['USED_HISTORICAL_FIXTURE','SYNTHETIC_TRANSPORT_TEST'].includes(input.sourceClass),'REAL_SOURCE_NOT_ADMITTED');
  assert.equal(input.universeComplete,true,'UNIVERSE_COMPLETENESS_REQUIRED');
  assert.equal(input.masterComplete,true,'MASTER_COMPLETENESS_REQUIRED');
  assert.equal(input.sessionDate,new Date(instant(input.timestamp)+32400000).toISOString().slice(0,10),'SESSION_DATE_MISMATCH');
  exposedDate(input.sessionDate);
  assert.ok(selectionSchedule(input.sessionDate).includes(iso(instant(input.timestamp))),'INVALID_DECISION_SCHEDULE');
  assert.equal(typeof input.sessionEnd,'boolean','SESSION_END_BOOLEAN_REQUIRED');
  if(input.sessionEnd)assert.equal(iso(instant(input.timestamp)),selectionSchedule(input.sessionDate).at(-1),'SESSION_END_TIME_MISMATCH');
  assert.ok(Array.isArray(input.universe)&&input.universe.length>0,'FULL_UNIVERSE_REQUIRED');
  const seen=new Set(),sourceCodes=new Set(),universe=[];
  for(const row of input.universe){
    const symbol=String(row?.symbol??'').toUpperCase();
    assert.match(symbol,/^[0-9A-Z]{4}\.T$/,'INVALID_SYMBOL');assert.ok(!seen.has(symbol),'DUPLICATE_UNIVERSE_MEMBER');seen.add(symbol);
    assert.ok(typeof row.sourceCode==='string'&&row.sourceCode.length>0,'SOURCE_CODE_REQUIRED');
    assert.ok(!sourceCodes.has(row.sourceCode),'DUPLICATE_SOURCE_CODE');sourceCodes.add(row.sourceCode);
    assert.ok(typeof row.sector==='string'&&row.sector.length>0,'SECTOR_REQUIRED');
    assert.ok(typeof row.marketCode==='string'&&row.marketCode.length>0,'MARKET_CODE_REQUIRED');
    assert.ok(typeof row.productCategory==='string'&&row.productCategory.length>0,'PRODUCT_CATEGORY_REQUIRED');
    assert.ok(instant(row.effectiveAt)<=instant(input.timestamp),'FUTURE_MASTER_ROW');
    assert.ok(Array.isArray(row.bars),'BARS_REQUIRED');
    const bars=row.bars.map((bar,index)=>canonicalBar(bar,symbol,input.timestamp,input.sessionDate,index)).sort((a,b)=>instant(a.timestamp)-instant(b.timestamp));
    for(let i=1;i<bars.length;i++)assert.ok(instant(bars[i].timestamp)>instant(bars[i-1].timestamp),'DUPLICATE_OR_NONMONOTONIC_BAR');
    universe.push({sourceCode:row.sourceCode,symbol,sector:row.sector,market:row.marketCode,productCategory:row.productCategory,effectiveAt:iso(instant(row.effectiveAt)),bars});
  }
  assert.equal(input.memberSetSha256,memberHash(universe),'MEMBER_SET_HASH_MISMATCH');
  const h=input.health;
  assert.ok(h&&typeof h==='object','HEALTH_REQUIRED');
  assert.equal(h.connected,true,'SOURCE_DISCONNECTED');assert.equal(h.workbookHealthy,true,'WORKBOOK_UNHEALTHY');assert.equal(h.stale,false,'SOURCE_STALE');assert.equal(h.rssError,false,'SOURCE_CELL_ERROR');
  return {...input,timestamp:iso(instant(input.timestamp)),universe};
}

function verifyAssets(root,selectorModel,entryModel,selectorFreeze){
  const canonicalEntry=JSON.parse(fs.readFileSync(path.join(root,'predict/research/phase57-msh-entry-v1-model.json')));
  const canonicalSelector=JSON.parse(fs.readFileSync(path.join(root,'predict/research/phase57-selector-minimal-hybrid-development-model.json')));
  const canonicalFreeze=JSON.parse(fs.readFileSync(path.join(root,'predict/research/phase57-selector-minimal-hybrid-development-freeze.json')));
  assert.equal(digest(fs.readFileSync(path.join(root,'predict/research/phase57-msh-entry-v1-model.json'))),MODEL,'MSH_MODEL_HASH_MISMATCH');
  assert.equal(digest(fs.readFileSync(path.join(root,'predict/research/phase57-selector-minimal-hybrid-development-model.json'))),SELECTOR_MODEL_FILE_SHA,'SELECTOR_MODEL_FILE_HASH_MISMATCH');
  assert.equal(digest(fs.readFileSync(path.join(root,'predict/research/phase57-selector-minimal-hybrid-development-freeze.json'))),SELECTOR_FREEZE_FILE_SHA,'SELECTOR_FREEZE_FILE_HASH_MISMATCH');
  assert.deepEqual(entryModel,canonicalEntry,'ENTRY_MODEL_OVERRIDE_FORBIDDEN');assert.deepEqual(selectorModel,canonicalSelector,'SELECTOR_MODEL_OVERRIDE_FORBIDDEN');assert.deepEqual(selectorFreeze,canonicalFreeze,'SELECTOR_FREEZE_OVERRIDE_FORBIDDEN');
  const {modelDigest,...modelCore}=selectorModel;assert.equal(hash(modelCore),modelDigest,'SELECTOR_MODEL_SELF_HASH_MISMATCH');
  const {freezeSha256,...freezeCore}=selectorFreeze;assert.equal(hash(freezeCore),freezeSha256,'SELECTOR_FREEZE_SELF_HASH_MISMATCH');
  assert.equal(selectorModel.modelDigest,SELECTOR_MODEL_DIGEST,'SELECTOR_MODEL_DIGEST_MISMATCH');
  assert.equal(selectorFreeze.modelDigest,SELECTOR_MODEL_DIGEST,'SELECTOR_FREEZE_MODEL_MISMATCH');
  assert.equal(selectorFreeze.freezeSha256,SELECTOR_FREEZE_SHA,'SELECTOR_FREEZE_SHA_MISMATCH');
  assert.equal(entryModel.selectorModelDigest,SELECTOR_MODEL_DIGEST,'ENTRY_SELECTOR_MODEL_MISMATCH');
  assert.equal(entryModel.selectorFreezeSHA,SELECTOR_FREEZE_SHA,'ENTRY_SELECTOR_FREEZE_MISMATCH');
  assert.equal(entryModel.threshold,0.6,'ENTRY_THRESHOLD_MISMATCH');
  assert.equal(entryModel.validationOpened,false,'VALIDATION_MUST_REMAIN_CLOSED');
  assert.equal(entryModel.artifactClass,'OFFLINE_DEVELOPMENT_CANDIDATE_NOT_PRODUCTION','ENTRY_ARTIFACT_CLASS_MISMATCH');
  assert.deepEqual(entryModel.features,ENTRY_CONTRACT.features,'ENTRY_FEATURE_CONTRACT_MISMATCH');
  for(const value of [...Object.values(FROZEN_MAIN_POLICY).filter(x=>typeof x==='boolean'),...Object.values(entryModel.safety??{}),...Object.values(ENTRY_SAFETY)])assert.equal(value,false,'UNSAFE_FLAG');
}

class FrozenMshEntry{
  constructor(date,model){this.date=date;this.model=model;this.states=new Map();this.last=-Infinity;}
  step(selection,prefixes,sourceClass){
    const t=instant(selection.featureCutoff);assert.ok(t>this.last,'ENTRY_NONMONOTONIC');this.last=t;
    const present=new Set(selection.selected.map(x=>x.symbol)),events=[],transitions=[];
    for(const [symbol,state] of this.states)if(state.state==='WATCHING'&&!present.has(symbol)){state.state='EXPIRED';transitions.push({symbol,at:selection.featureCutoff,to:'EXPIRED',reason:'NOT_SELECTED_ON_COMPLETE_SNAPSHOT'});}
    for(const candidate of selection.selected){
      const state=this.states.get(candidate.symbol)??{state:'UNSEEN',firstSelectionTimestamp:selection.featureCutoff,priorSelectionCount:0,entryCount:0};
      const before=state.state,priceReference=prefixes[candidate.symbol].at(-1)?.close;
      if(state.state==='UNSEEN')state.state='WATCHING';
      const core={eventId:`${this.date}|${selection.featureCutoff}|${candidate.symbol}`,symbolSessionId:`${this.date}|${candidate.symbol}`,sessionDate:this.date,symbol:candidate.symbol,decisionTimestamp:selection.featureCutoff,hybridRank:candidate.hybridRank,hybridScore:candidate.hybridScore,priorSelectionCount:state.priorSelectionCount,firstSelectionTimestamp:state.firstSelectionTimestamp,sourceClass,selectionLineage:selection.evidence.evidenceSha256};
      let pair=null,featureStatus='READY',decision={action:'WATCH',direction:null,reason:'BLOCKED_FEATURES'};
      try{
        pair=[1,-1].map(direction=>buildDirectionFeatures({symbol:candidate.symbol,decisionTimestamp:selection.featureCutoff,bars:prefixes[candidate.symbol],rank:candidate.hybridRank,score:candidate.hybridScore,priceReference,firstSelectionTimestamp:state.firstSelectionTimestamp,priorSelectionCount:state.priorSelectionCount,direction}));
        if(!['ENTERED','EXPIRED'].includes(state.state)){
          const scored=pair.map(row=>({direction:row.direction,probability:score(row,this.model)})).sort((a,b)=>b.probability-a.probability);
          if(scored[0].probability===scored[1].probability)decision={action:'WATCH',direction:null,reason:'DIRECTION_TIE'};
          else decision={action:scored[0].probability>this.model.threshold?'ENTER':'WATCH',direction:scored[0].probability>this.model.threshold?scored[0].direction:null,probability:scored[0].probability,longProbability:scored.find(x=>x.direction===1).probability,shortProbability:scored.find(x=>x.direction===-1).probability,reason:scored[0].probability>this.model.threshold?'ABOVE_SINGLE_THRESHOLD':'NOT_ABOVE_SINGLE_THRESHOLD'};
        }else decision={action:'NO_ACTION',direction:null,reason:state.state};
      }catch(error){featureStatus=String(error.message);}
      if(decision.action==='ENTER'){state.state='ENTERED';state.entryCount++;assert.equal(state.entryCount,1,'REENTRY_VIOLATION');}
      state.priorSelectionCount++;this.states.set(candidate.symbol,state);
      if(before!==state.state)transitions.push({symbol:candidate.symbol,at:selection.featureCutoff,from:before,to:state.state,reason:decision.reason});
      events.push({...core,stateBefore:before,stateAfter:state.state,entryCount:state.entryCount,featureStatus,directionFeatures:pair,decision,safety:ENTRY_SAFETY});
    }
    return {events,transitions,status:'COMPLETE'};
  }
  close(at){const transitions=[];for(const [symbol,state] of this.states)if(state.state==='WATCHING'){state.state='EXPIRED';transitions.push({symbol,at,to:'EXPIRED',reason:'SESSION_CLOSE'});}return transitions;}
}

class FrozenV4Manager{
  constructor({entryPrice,direction,sessionDate,contextBars,analogPool}){
    this.entryPrice=entryPrice;this.direction=direction===1?'LONG':'SHORT';this.sign=direction;this.sessionDate=sessionDate;this.analogPool=analogPool;this.observed=[];this.downsideHistory=[];this.neutralLossStreak=0;this.winnerExitStreak=0;this.mfe=0;
    const ranges=contextBars.slice(-6).map(b=>(b.high-b.low)/b.close*100).filter(Number.isFinite);this.adverseExcursionScalePct=ranges.length?ranges.reduce((a,b)=>a+b,0)/ranges.length:null;
  }
  step(bar,timestamp,{sessionEnd=false}={}){
    this.observed.push(bar);const px=bar.close,currentReturnPct=this.sign*(px/this.entryPrice-1)*100,barMfe=this.sign*(this.sign===1?bar.high/this.entryPrice-1:bar.low/this.entryPrice-1)*100;
    this.mfe=Math.max(this.mfe,barMfe);const captureRatio=this.mfe>0?currentReturnPct/this.mfe:null;
    const baseScore=scoreP25ExitV2StateConditioned({entryPrice:this.entryPrice,direction:this.direction,observedBars:this.observed,timestamp,sessionDate:this.sessionDate,analogPool:this.analogPool});
    const h1=baseScore.horizonScores?.find(x=>x.horizonBars===1);const prior=[...this.downsideHistory];if(Number.isFinite(Number(h1?.downsideProbability)))this.downsideHistory.push(Number(h1.downsideProbability));
    const gate=decideP25ExitV4({baseScore,currentReturnPct,mfePct:this.mfe,captureRatio,downsideHistory:prior,neutralLossStreak:this.neutralLossStreak,winnerExitStreak:this.winnerExitStreak,adverseExcursionScalePct:this.adverseExcursionScalePct});
    this.neutralLossStreak=gate.neutralLossStreak;this.winnerExitStreak=gate.winnerExitStreak;
    const exit=sessionEnd||gate.decision==='EXIT';return {timestamp,action:exit?'EXIT':'HOLD',...(exit?{exitPrice:px,exitReason:sessionEnd?'SESSION_END':gate.reason}:{}),baseScore,gate,currentReturnPct,mfePct:this.mfe,captureRatio,policySha256:P25_EXIT_V4_POLICY_SHA256};
  }
}

export function createFrozenMainEngine({root=process.cwd(),analogPool,selectorModel,entryModel,selectorFreeze}={}){
  selectorModel??=JSON.parse(fs.readFileSync(path.join(root,'predict/research/phase57-selector-minimal-hybrid-development-model.json')));
  entryModel??=JSON.parse(fs.readFileSync(path.join(root,'predict/research/phase57-msh-entry-v1-model.json')));
  selectorFreeze??=JSON.parse(fs.readFileSync(path.join(root,'predict/research/phase57-selector-minimal-hybrid-development-freeze.json')));
  verifyAssets(root,selectorModel,entryModel,selectorFreeze);assert.equal(validateP25ExitV2AnalogPool(analogPool).ready,true,'ANALOG_POOL_NOT_CAUSAL');
  let sessionDate=null,last=-Infinity,entry=null,ledger=createOfflineShadowLedger(),closed=false,halted=false;const positions=new Map(),barHistory=new Map(),sourceMap=new Map(),masterMap=new Map();
  function reduce(raw){
      assert.equal(closed,false,'ENGINE_SEALED');const point=validatePoint(raw),t=instant(point.timestamp);assert.ok(t>last,'POINT_NONMONOTONIC');last=t;
      if(sessionDate===null){sessionDate=point.sessionDate;entry=new FrozenMshEntry(sessionDate,entryModel);}assert.equal(point.sessionDate,sessionDate,'CROSS_SESSION_INPUT');
      for(const row of point.universe){
        if(sourceMap.has(row.sourceCode))assert.equal(sourceMap.get(row.sourceCode),row.symbol,'SOURCE_CODE_SYMBOL_DRIFT');else sourceMap.set(row.sourceCode,row.symbol);
        const master={sourceCode:row.sourceCode,sector:row.sector,market:row.market,productCategory:row.productCategory};
        if(masterMap.has(row.symbol))assert.deepEqual(masterMap.get(row.symbol),master,'INTRASESSION_MASTER_DRIFT');else masterMap.set(row.symbol,master);
        for(const bar of row.bars){const key=`${row.symbol}|${bar.timestamp}`;if(barHistory.has(key))assert.equal(barHistory.get(key),hash(bar),'HISTORICAL_BAR_REVISION');else barHistory.set(key,hash(bar));}
      }
      const prefixes=Object.fromEntries(point.universe.map(row=>[row.symbol,row.bars]));
      const selection=runPhase57MinimalHybrid({featureCutoff:point.timestamp,entries:point.universe.map(row=>({symbol:row.symbol,sector:row.sector,market:row.market,bars:row.bars})),model:selectorModel});
      const entryResult=entry.step(selection,prefixes,point.sourceClass);
      const opportunities=entryResult.events.filter(x=>x.decision.action==='ENTER').map(event=>({...buildEntryTimeOpportunity(event,{recentCloses:prefixes[event.symbol].slice(-7).map(x=>x.close)}),entryPrice:prefixes[event.symbol].at(-1).close}));
      const exits=[],management=[];
      for(const [eventId,p] of positions){
        const bar=prefixes[p.symbol]?.at(-1);assert.ok(bar&&instant(bar.availableAt)<=t,'OPEN_POSITION_MARK_MISSING');
        assert.equal(instant(bar.availableAt),t,'OPEN_POSITION_MANAGEMENT_BAR_MISSING');
        const v4=p.v4.step(bar,point.timestamp,{sessionEnd:point.sessionEnd===true});const v5=p.v5.step({timestamp:point.timestamp,close:bar.close,v4});management.push({eventId,symbol:p.symbol,v4,v5});if(v5.decision)exits.push(v5.decision);
      }
      const marks=point.universe.flatMap(row=>row.bars.length?[{symbol:row.symbol,close:row.bars.at(-1).close}]:[]);
      const trace=ledger.step({timestamp:point.timestamp,sessionDate:point.sessionDate,marks,entries:point.sessionEnd?[]:opportunities,exitDecisions:exits});
      for(const x of exits)positions.delete(x.eventId);
      const accepted=new Set(trace.entries.map(x=>x.eventId));
      for(const opportunity of opportunities.filter(x=>accepted.has(x.eventId))){const context=prefixes[opportunity.symbol];positions.set(opportunity.eventId,{symbol:opportunity.symbol,v4:new FrozenV4Manager({entryPrice:opportunity.entryPrice,direction:opportunity.direction,sessionDate,contextBars:context,analogPool}),v5:new Bar5Manager({eventId:opportunity.eventId,symbol:opportunity.symbol,direction:opportunity.direction,entryPrice:opportunity.entryPrice,entryTimestamp:point.timestamp})});}
      if(point.sessionEnd===true){entryResult.transitions.push(...entry.close(point.timestamp));assert.equal(positions.size,0,'SESSION_END_OPEN_POSITION');closed=true;}
      const safety={...FROZEN_MAIN_POLICY};
      return {raw:[{timestamp:point.timestamp,sourceClass:point.sourceClass,memberSetSha256:point.memberSetSha256,universeCount:point.universe.length}],normalized:[...point.universe.flatMap(x=>x.bars.slice(-1).map(bar=>({symbol:x.symbol,...bar})))],decisions:[{timestamp:point.timestamp,selection,entry:entryResult,management,entryBlockedAtSessionEnd:point.sessionEnd===true&&opportunities.length>0,safety}],ledger:[trace],health:[{timestamp:point.timestamp,status:'HEALTHY_OFFLINE_SHADOW',shadowDecisionAllowed:true,executionDecisionAllowed:false,executionAllowed:false,transmitted:false}],reference:[],mismatch:[],report:[]};
  }
  return {
    step(raw){if(halted)throw Error('ENGINE_HALTED');try{return reduce(raw);}catch(error){halted=true;throw error;}},
    snapshot(){return {sessionDate,lastTimestamp:last===-Infinity?null:iso(last),closed,halted,openPositionCount:positions.size,ledger:ledger.snapshot(),policy:FROZEN_MAIN_POLICY};},
  };
}

export function frozenMainMemberSetSha256(universe){return memberHash(universe);}
