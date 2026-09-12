import assert from 'node:assert/strict';
import {FEATURES} from './phase57-minimal-stateful-entry.mjs';
import {FIT,solveWeightedLogistic,verifyFrozenRow} from './phase57-entry-development-fit.mjs';
export const mean=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:null;
export const median=a=>{const b=[...a].sort((x,y)=>x-y);return b.length?(b[Math.floor((b.length-1)/2)]+b[Math.floor(b.length/2)])/2:null;};
const jst=t=>new Date(t+32400000).toISOString();
export function labels(event,bars){
 const by=new Map();for(const b of bars){assert(!by.has(Date.parse(b.timestamp)));by.set(Date.parse(b.timestamp),b);}
 const result={};
 for(const h of [1,3,6]){
  let t=Date.parse(event.decisionTimestamp);const path=[];
  for(let i=0;i<h;i++){
   const clock=jst(t).slice(11,16);if(clock>='11:30'&&clock<'12:30')t=Date.parse(`${event.sessionDate}T12:30:00+09:00`);
   if(jst(t).slice(0,10)!==event.sessionDate||jst(t).slice(11,16)>='15:30'){path.push(null);break;}
   path.push(by.get(t));t+=300000;
  }
  if(path.length!==h||path.some(b=>!b)){result[h]=null;continue;}
  for(const b of path){assert.equal(b.sessionDate,event.sessionDate);assert.equal(Date.parse(b.availableAt),Date.parse(b.timestamp)+300000);assert(['open','high','low','close','volume'].every(k=>Number.isFinite(b[k])));assert(b.low>0&&b.high>=Math.max(b.open,b.close)&&b.low<=Math.min(b.open,b.close)&&b.volume>=0);}
  const anchor=event.priceReference;assert(Number.isFinite(anchor)&&anchor>0);
  const up=Math.max(0,...path.map(b=>(b.high/anchor-1)*10000)),down=Math.max(0,...path.map(b=>(1-b.low/anchor)*10000));
  const gross=(path.at(-1).close/anchor-1)*10000;
  const time=(v,fn)=>v===0?0:(Date.parse(path.find(b=>fn(b)===v).availableAt)-Date.parse(event.decisionTimestamp))/60000;
  result[h]={LONG:{gross,net:gross-5,mfe:up,mae:down,timeToMfe:time(up,b=>(b.high/anchor-1)*10000)},SHORT:{gross:-gross,net:-gross-5,mfe:down,mae:up,timeToMfe:time(down,b=>(1-b.low/anchor)*10000)}};
 }
 return result;
}
export function fitRows(events){
 const usable=events.filter(e=>e.directionFeatures&&e.labels[3]);
 const groups=new Map();for(const e of usable){if(!groups.has(e.sessionDate))groups.set(e.sessionDate,new Map());const s=groups.get(e.sessionDate);if(!s.has(e.symbol))s.set(e.symbol,0);s.set(e.symbol,s.get(e.symbol)+1);}
 assert(groups.size>0,'NO_TRAINING_ROWS');const x=[],y=[],w=[];
 for(const e of usable)for(const row of e.directionFeatures){verifyFrozenRow(row);x.push(FEATURES.map(k=>row.features[k]));y.push(Number(e.labels[3][row.direction===1?'LONG':'SHORT'].net>0));w.push(1/(groups.size*groups.get(e.sessionDate).size*groups.get(e.sessionDate).get(e.symbol)*2));}
 return {...solveWeightedLogistic(x,y,w),trainingDirectionalRows:x.length,positive:y.filter(Boolean).length,negative:y.filter(v=>!v).length};
}
export function probability(row,m){const z=m.intercept+FEATURES.reduce((s,k,i)=>s+m.weights[i]*(row.features[k]-m.means[i])/m.scales[i],0);return z>=0?1/(1+Math.exp(-z)):Math.exp(z)/(1+Math.exp(z));}
export function stateful(events,m,threshold){
 assert(FIT.threshold.candidates.includes(threshold));const entered=new Set(),seen=new Set(),ledger=[];
 let watch=0,noAction=0;
 for(const e of events){assert(!Object.hasOwn(e,'labels')&&!Object.hasOwn(e,'target'),'OUTCOME_IN_STATE_INPUT');assert(!seen.has(e.eventId),'DUPLICATE_EVENT');seen.add(e.eventId);const key=e.symbolSessionId;
  if(entered.has(key)||e.stateBefore==='EXPIRED'){noAction++;ledger.push({eventId:e.eventId,status:'NO_ACTION'});continue;}
  if(!e.directionFeatures){watch++;ledger.push({eventId:e.eventId,status:'WATCH',reason:'BLOCKED_FEATURES'});continue;}
  const [l,s]=e.directionFeatures.map(r=>probability(r,m));
  if(l===s||Math.max(l,s)<=threshold){watch++;ledger.push({eventId:e.eventId,status:'WATCH',longProbability:l,shortProbability:s});continue;}
  entered.add(key);ledger.push({eventId:e.eventId,status:'ENTER',direction:l>s?'LONG':'SHORT',longProbability:l,shortProbability:s});
 }
 return {ledger,watch,noAction,entered:entered.size,expired:new Set(events.map(e=>e.symbolSessionId)).size-entered.size};
}
export function clustering(rows,value){
 const groups=new Map();for(const r of rows){const v=value(r);if(!Number.isFinite(v))continue;if(!groups.has(r.sessionDate))groups.set(r.sessionDate,[]);groups.get(r.sessionDate).push(v);}
 const a=[...groups.values()],N=a.reduce((s,g)=>s+g.length,0),k=a.length;if(k<2||N<=k)return {nominalN:N,sessions:k,icc:null,designEffect:null,effectiveN:null,reason:'INSUFFICIENT_WITHIN_BETWEEN_VARIATION'};
 const grand=mean(a.flat()),msb=a.reduce((s,g)=>s+g.length*(mean(g)-grand)**2,0)/(k-1),msw=a.reduce((s,g)=>s+g.reduce((q,v)=>q+(v-mean(g))**2,0),0)/(N-k);
 const n0=(N-a.reduce((s,g)=>s+g.length**2,0)/N)/(k-1),den=msb+(n0-1)*msw;
 if(den===0)return {nominalN:N,sessions:k,icc:null,designEffect:null,effectiveN:null,reason:'ZERO_VARIANCE'};
 const icc=(msb-msw)/den,de=1+(N/k-1)*Math.max(0,icc);return {nominalN:N,sessions:k,icc,designEffect:de,effectiveN:N/de,method:'ONE_WAY_UNBALANCED_ICC; APPROX_MEAN_CLUSTER_SIZE_DESIGN_EFFECT; NEGATIVE_ICC_CLIPPED_ONLY_FOR_DESIGN_EFFECT'};
}
export function metrics(events,decision,sessionDates){
 const by=new Map(events.map(e=>[e.eventId,e]));const entered=decision.ledger.filter(r=>r.status==='ENTER').map(r=>({...by.get(r.eventId),direction:r.direction}));
 const values=h=>entered.flatMap(e=>e.labels[h]?[e.labels[h][e.direction]]:[]);
 const h={};for(const n of [1,3,6]){const v=values(n);h[n]={complete:v.length,missing:entered.length-v.length,grossPositiveRate:mean(v.map(x=>Number(x.gross>0))),costAdjustedPositiveRate:mean(v.map(x=>Number(x.net>0))),meanGross:mean(v.map(x=>x.gross)),meanNet:mean(v.map(x=>x.net)),medianNet:median(v.map(x=>x.net))};}
 const sessions=sessionDates.map(date=>{const es=entered.filter(e=>e.sessionDate===date),v=es.flatMap(e=>e.labels[3]?[e.labels[3][e.direction].net]:[]);return {sessionDate:date,events:events.filter(e=>e.sessionDate===date).length,enter:es.length,complete3:v.length,meanNet3:mean(v)};});
 const active=sessions.filter(s=>s.meanNet3!==null),m3=values(3),m1=values(1);
 return {events:events.length,uniqueSymbols:new Set(events.map(e=>e.symbol)).size,uniqueSymbolSessions:new Set(events.map(e=>e.symbolSessionId)).size,repeatedSelections:events.length-new Set(events.map(e=>e.symbolSessionId)).size,enter:entered.length,watch:decision.watch,noAction:decision.noAction,expired:decision.expired,coverage:events.length?entered.length/events.length:null,opportunityCoverage:new Set(events.map(e=>e.symbolSessionId)).size?entered.length/new Set(events.map(e=>e.symbolSessionId)).size:null,horizons:h,immediateAdverse:mean(m1.map(v=>Number(v.mae>0))),meanMFE3:mean(m3.map(v=>v.mfe)),meanMAE3:mean(m3.map(v=>v.mae)),medianMFE3:median(m3.map(v=>v.mfe)),medianMAE3:median(m3.map(v=>v.mae)),meanDelayMinutes:mean(entered.map(e=>e.minutesSinceFirstSelection)),medianDelayMinutes:median(entered.map(e=>e.minutesSinceFirstSelection)),sessions,medianActiveSessionNet3:median(active.map(s=>s.meanNet3)),positiveSessions:active.filter(s=>s.meanNet3>0).length,negativeSessions:active.filter(s=>s.meanNet3<0).length,zeroSessions:active.filter(s=>s.meanNet3===0).length,noLabeledEnterSessions:sessionDates.length-active.length,sessionStability:sessionDates.length?active.filter(s=>s.meanNet3>0).length/sessionDates.length:null,LONG:entered.filter(e=>e.direction==='LONG').length,SHORT:entered.filter(e=>e.direction==='SHORT').length,clustering:clustering(entered,e=>e.labels[3]?.[e.direction]?.net)};
}
