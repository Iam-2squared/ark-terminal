// Inference adapter only. Calls the immutable Frozen Selector modules; no refit.
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {assembleLongOnlyL0Rows,normalizeAndAggregateMinuteRows} from '../predict/long-only/phase57-long-only-integrated-dataset.js';
import {buildL1CrossSectionDataset} from '../predict/long-only/phase57-long-only-l1-cross-section.js';
import {scoreL2Candidate} from '../predict/long-only/phase57-long-only-l2-selector-v1.js';
import {normalizeMinuteProvenance,measureCorrectedRow} from '../predict/long-only/phase57-long-only-corrected-measurement.js';
const [cache,day,previous,out]=process.argv.slice(2);
const sha=x=>createHash('sha256').update(x).digest('hex');
function pages(date,kind){const ps=JSON.parse(fs.readFileSync(`${cache}/${date}/${kind}-pages.json`));for(const p of ps)if(sha(p.responseText)!==p.responseSha256)throw Error('PAGE_HASH');const rows=ps.flatMap(p=>JSON.parse(p.responseText).data);if(rows.some(x=>x.Date!==date))throw Error('DATE');return rows;}
const daily=pages(day,'daily'),master=pages(day,'master'),prior=pages(previous,'daily'),raw=pages(day,'minute');
const l0=assembleLongOnlyL0Rows({dailyRows:daily,masterRows:master,warmupDailyRows:prior});
const n=normalizeAndAggregateMinuteRows(raw),minutes=normalizeMinuteProvenance(raw),sectorBySymbol={};
for(const x of master)sectorBySymbol[day+'|'+x.Code]=String(x.S17??x.Sec17??x.Sector17Code??x.Sector33Code??x.S33??'UNKNOWN');
const built=buildL1CrossSectionDataset({partition:'DEVELOPMENT_A',dailyRows:l0.rows,bars5m:n.bars,terminalAuctions:n.terminalAuctions,sectorBySymbol});
const spec=JSON.parse(fs.readFileSync('predict/research/phase57-long-only-frozen-selector-v1.json')).freezePayload;
const bars=new Map(),dmap=new Map(l0.rows.map(x=>[day+'|'+x.symbol,x]));for(const x of n.bars){const key=day+'|'+x.symbol;if(!bars.has(key))bars.set(key,[]);bars.get(key).push(x);}
const groups=new Map();
for(const f of built.featureRows){
 const key=day+'|'+f.symbol;
 // The price calculation is given only the causal prefix. Its evaluator fields are discarded.
 const bb=bars.get(key).filter(x=>x.availableAtJst<=f.decisionAtJst),mm=minutes.get(key).filter(x=>x.availableMinute<=Number(f.decisionTimeJst.slice(0,2))*60+Number(f.decisionTimeJst.slice(3)));
 const q=measureCorrectedRow({feature:f,bars:bb,minutes:mm});
 if(q.decisionPriceValid!==1||!(q.decisionPrice>75)||q.referenceAgeMin<0||q.referenceAgeMin>5)continue;
 const score=scoreL2Candidate(f,spec.selectorSpecification.model.configuration);if(!Number.isFinite(score))throw Error('NONFINITE_FROZEN_SCORE');
 const latest=mm.at(-1);const stamp=day+'T'+String(Math.floor(latest.availableMinute/60)).padStart(2,'0')+':'+String(latest.availableMinute%60).padStart(2,'0')+':00+09:00';
 const row={sessionDate:day,symbol:f.symbol,decisionTimestamp:f.decisionAtJst,decisionTimeJst:f.decisionTimeJst,decisionPrice:q.decisionPrice,decisionPriceAvailableAtJst:stamp,referenceAgeMin:q.referenceAgeMin,savedV1Score:score,selectorEventId:day+'|'+f.decisionAtJst+'|'+f.symbol};
 if(!groups.has(f.decisionAtJst))groups.set(f.decisionAtJst,[]);groups.get(f.decisionAtJst).push(row);
}
const selected=[];for(const time of spec.selectorSpecification.ranking.decisionTimesJst){const g=groups.get(day+'T'+time+':00+09:00')??[];g.sort((a,b)=>b.savedV1Score-a.savedV1Score||a.symbol.localeCompare(b.symbol));selected.push(...g.slice(0,5).map((x,i)=>({...x,newEligibleRank:i+1})));}
fs.writeFileSync(out,JSON.stringify({members:selected,audit:{day,previous,candidates:selected.length,decisionGroups:groups.size,l0:l0.audit.exclusionCounts,featureRows:built.featureRows.length,selectorSourceUnchanged:true,legacyL0Admission:true,legacyL0Limitation:'Frozen L0 uses same-date daily validity/corporate-action/adjustment metadata; inherited retrospective upstream admission, not independently PIT-certified. Additional WHO/RECENT/NOW do not use current daily quotes.'}}),{flag:'wx'});
