/**
 * Read-only mapping audit between saved RssChart bars and frozen State9 RC2.
 * RC2 expects J-Quants source interval and normalized exact decimal OHLC;
 * MarketSpeed II raw yen prices are NOT a drop-in substitute.
 */
import {readNo11SavedChartEvidence} from './no11_saved_chart_evidence_audit.mjs';
import {compareNo11SavedChartParity} from './no11_saved_chart_parity.mjs';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
const fail=x=>{throw Error(x)};
const localMinute=s=>{const [h,m]=s.slice(11,16).split(':').map(Number);return h*60+m;};
export function auditNo11State9InputBoundary({file,now=new Date()}={}){
 const checked=readNo11SavedChartEvidence({file,now});
 const raw=fs.readFileSync(file);
 const obj=JSON.parse(raw.toString('utf8').replace(/^\uFEFF/,''));
 const parity=compareNo11SavedChartParity({evidence:obj,now});
 const best=parity.bestObservedCombination;
 const sessions={};
 for(const period of ['1M','5M']){
  const rows=obj.periods[period].rows;
  const sorted=[...rows].sort((a,b)=>a.label.localeCompare(b.label));
  const dayCounts={},gaps=[],nonMonotone=0;
  const dayRanges=new Map(),crossSessionBoundaries=[];
  for(let i=0;i<sorted.length;i++){
   const day=sorted[i].label.slice(0,10);
   dayCounts[day]=(dayCounts[day]??0)+1;
   const previousRange=dayRanges.get(day);
   if(!previousRange)dayRanges.set(day,{day,firstLabel:sorted[i].label,lastLabel:sorted[i].label,count:1});
   else {previousRange.lastLabel=sorted[i].label;previousRange.count++;}
   if(i===0)continue;
   if(day!==sorted[i-1].label.slice(0,10)){
    crossSessionBoundaries.push({
     previousLabel:sorted[i-1].label,currentLabel:sorted[i].label,
     classification:'CROSS_SESSION_ARCHIVE_BOUNDARY_NOT_MISSING_BAR'
    });
    continue;
   }
   const prev=localMinute(sorted[i-1].label),cur=localMinute(sorted[i].label);
   const step=period==='1M'?1:5;
   // Lunch breaks, terminal auction, and partial archive windows are not
   // classified as missing market data from this local receipt alone.
   if(cur<=prev)nonMonotone++;
   if(cur-prev>step){
    const lunch=prev<=690&&cur>=750;
    const priorEnd=prev===690||prev===930;
    const classification=lunch?'EXPECTED_LUNCH_BREAK_BOUNDARY':
      priorEnd?'SESSION_BOUNDARY_OR_TERMINAL_AUCTION_REVIEW':
      'UNEXPLAINED_OBSERVED_LABEL_GAP_REQUIRES_SOURCE_REVIEW';
    gaps.push({
     day,previousLabel:sorted[i-1].label,currentLabel:sorted[i].label,
     deltaMinutes:cur-prev,nominalStepMinutes:step,
     classification,missingMarketBarsCertified:false
    });
   }
  }
  sessions[period]={rows:sorted.length,sessionCounts:dayCounts,
   observedIntraSessionGaps:gaps.slice(0,20),
   observedIntraSessionGapCount:gaps.length,
   unexplainedObservedLabelGaps:gaps.filter(g=>g.classification==='UNEXPLAINED_OBSERVED_LABEL_GAP_REQUIRES_SOURCE_REVIEW').length,
   expectedLunchBoundaries:gaps.filter(g=>g.classification==='EXPECTED_LUNCH_BREAK_BOUNDARY').length,
   dayRanges:[...dayRanges.values()],
   crossSessionBoundaries,
   archiveWindowPartialOrCompleteUnknown:true,
   previousSessionBaselineUCertified:false,
   previousSessionPRefCertified:false,
   nonMonotone,completeSessionCertified:false};
 }
 const blockers=[
  'VENDOR_1M_LABEL_START_END_NOT_CERTIFIED',
  'VENDOR_1M_AUCTION_AND_SESSION_INTERVAL_MAPPING_NOT_CERTIFIED',
  'JQUANTS_V2_SOURCE_IDENTITY_NOT_EQUAL_TO_RSS',
  'PREVIOUS_SESSION_U_AND_P_REF_NOT_AVAILABLE',
  'EXACT_NORMALIZED_DECIMAL_OHLC_ADAPTER_NOT_CERTIFIED',
  'SCHEDULED_ORDINAL_AND_KNOWN_AT_NOT_CERTIFIED',
  'ORIGINAL_FROZEN_STATE9_KERNEL_NOT_EXECUTED',
  'SINGLE_SYMBOL_NOT_MARKETWIDE_SELECTOR'
 ];
 return Object.freeze({
  schemaId:'ARK_NO11_STATE9_RSS_INPUT_BOUNDARY_AUDIT_V1',
  status:'MARKET_SOURCE_OBSERVED_STATE9_NOT_CONNECTED',
  evidenceSha256:checked.localFileSha256,
  symbol:checked.symbol,periods:sessions,
  observedParity:{matched:best.matched,compared:best.completeGroupsCompared,
   unmatchedFive:best.unmatchedFive,oneMinuteLabel:best.oneMinuteLabel,
   fiveMinuteLabel:best.fiveMinuteLabel},
  frozenContractSource:'research/state9-structural-exit-v2-20261003/FROZEN_SOURCE/input_gate.py',
  blockers,
  nativeState9Connected:false,nativeState9ParityCertified:false,
  originalFrozenSelectorConnected:false,originalFrozenFirstEntryConnected:false,
  productionReady:false,orderTransmission:false
 });
}
