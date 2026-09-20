// Research adapter: immutable CURRENT Entry and selector projection, no fit or production writes.
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {assembleLongOnlyL0Rows,normalizeAndAggregateMinuteRows} from '../predict/long-only/phase57-long-only-integrated-dataset.js';
import {buildL1CrossSectionDataset} from '../predict/long-only/phase57-long-only-l1-cross-section.js';
import {projectL2Features,scoreL2Candidate} from '../predict/long-only/phase57-long-only-l2-selector-v1.js';
import {assertCurrentEntryAssets,evaluateLongOnlyTransferSession,normalizeEntryBars} from '../predict/long-only/phase57-long-only-current-entry-transfer.js';
const [cache,day,previous,membersFile,out]=process.argv.slice(2),read=f=>JSON.parse(fs.readFileSync(f)),sha=x=>createHash('sha256').update(x).digest('hex');
function pages(date,kind){const a=read(`${cache}/${date}/${kind}-pages.json`);for(const p of a)if(sha(p.responseText)!==p.responseSha256)throw Error('PAGE_HASH');const rows=a.flatMap(p=>JSON.parse(p.responseText).data);if(rows.some(x=>x.Date!==date))throw Error('DATE');return rows;}
const members=read(membersFile),n=normalizeAndAggregateMinuteRows(pages(day,'minute'));
const selections=members.map(x=>({...x,ridgeRank:x.newEligibleRank,ridgeScore:x.savedV1Score}));
const modelPath='predict/research/phase57-msh-entry-v1-model.json',model=read(modelPath);
assertCurrentEntryAssets({model,modelBytes:fs.readFileSync(modelPath),contractBytes:fs.readFileSync('predict/research/phase57-minimal-stateful-entry-contract.json'),implementationBytes:fs.readFileSync('scripts/lib/phase57-minimal-stateful-entry.mjs')});
const symbols=new Set(members.map(x=>x.symbol)),bars=new Map(),auctions=new Map();
for(const code of symbols){bars.set(code,normalizeEntryBars(n.bars.filter(x=>x.symbol===code)));auctions.set(code,n.terminalAuctions.filter(x=>x.symbol===code));}
const current=evaluateLongOnlyTransferSession({sessionDate:day,selections,barsBySymbol:bars,auctionsBySymbol:auctions,model});
const projected={},missing={};
if(previous!=='UNAVAILABLE'){
 const master=pages(day,'master'),l0=assembleLongOnlyL0Rows({dailyRows:pages(day,'daily'),masterRows:master,warmupDailyRows:pages(previous,'daily')}),sectors={};
 for(const x of master)sectors[day+'|'+x.Code]=String(x.S17??x.Sec17??x.Sector17Code??x.Sector33Code??x.S33??'UNKNOWN');
 const built=buildL1CrossSectionDataset({partition:'DEVELOPMENT_A',dailyRows:l0.rows,bars5m:n.bars,terminalAuctions:n.terminalAuctions,sectorBySymbol:sectors});
 const wanted=new Map(members.map(x=>[x.symbol+'|'+x.decisionTimeJst,x]));
 const config=read('predict/research/phase57-long-only-frozen-selector-v1.json').freezePayload.selectorSpecification.model.configuration;
 for(const f of built.featureRows){const m=wanted.get(f.symbol+'|'+f.decisionTimeJst);if(!m)continue;
  if(f.latestAvailableAtJst>f.decisionAtJst)throw Error('FUTURE_FROZEN_FEATURE');
  const score=scoreL2Candidate(f,config);if(Math.abs(score-m.savedV1Score)>1e-5)throw Error('SAVED_SELECTOR_SCORE_DRIFT');
  projected[m.selectorEventId]={features:projectL2Features(f),computedThrough:f.latestAvailableAtJst};
 }
}
for(const m of members)if(!projected[m.selectorEventId])missing[m.selectorEventId]=previous==='UNAVAILABLE'?'AUTHORIZED_PREVIOUS_DAILY_UNAVAILABLE':'FROZEN_FEATURE_ROW_UNAVAILABLE';
fs.writeFileSync(out,JSON.stringify({projected,missing,currentOpportunities:current.opportunities,currentTicks:current.ticks.map(x=>({symbolSessionId:x.symbolSessionId,evaluationTimestamp:x.evaluationTimestamp,status:x.status,reason:x.reason})),selectorChanged:false,currentEntryChanged:false}),{flag:'wx'});
