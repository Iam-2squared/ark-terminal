import {createHash} from 'node:crypto';
import {assertRuntimeAcquisitionAuthorization} from './phase57-long-only-acquisition-gate.js';

const API_ROOT='https://api.jquants.com/v2';
const sha=value=>createHash('sha256').update(value).digest('hex');
const stable=value=>value&&typeof value==='object'?(Array.isArray(value)?value.map(stable):Object.fromEntries(Object.keys(value).sort().map(k=>[k,stable(value[k])]))):value;
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
let nextProviderRequestAt=0;

export async function fetchJquantsPages({endpoint,query,apiKey,fetchImpl=globalThis.fetch,maxPages=100,requestBudget=null,minimumRequestIntervalMs=fetchImpl===globalThis.fetch?1100:0}={}){
  if(!['/equities/bars/daily','/equities/master','/equities/bars/minute'].includes(endpoint))throw new Error('endpoint is outside frozen J-Quants contract');
  if(!apiKey||typeof fetchImpl!=='function')throw new Error('API key and fetch implementation are required');
  const pages=[],keys=new Set();let paginationKey;
  for(let page=1;page<=maxPages;page++){
    const params=new URLSearchParams(Object.entries(query??{}).map(([k,v])=>[k,String(v)]));
    if(paginationKey)params.set('pagination_key',paginationKey);
    if(requestBudget){
      if(!Number.isInteger(requestBudget.remaining)||requestBudget.remaining<1)throw new Error('approved J-Quants provider request budget exhausted before network');
      requestBudget.remaining--;requestBudget.consumed=(requestBudget.consumed??0)+1;
    }
    const waitMs=Math.max(0,nextProviderRequestAt-Date.now());if(waitMs)await sleep(waitMs);
    nextProviderRequestAt=Date.now()+Math.max(0,Number(minimumRequestIntervalMs)||0);
    const response=await fetchImpl(`${API_ROOT}${endpoint}?${params}`,{cache:'no-store',redirect:'error',headers:{Accept:'application/json','x-api-key':apiKey},signal:fetchImpl===globalThis.fetch?AbortSignal.timeout(120000):undefined});
    if(!response?.ok)throw new Error(`J-Quants ${endpoint} failed with HTTP ${response?.status}`);
    const text=await response.text(),payload=JSON.parse(text);
    if(!Array.isArray(payload?.data))throw new Error(`J-Quants ${endpoint} payload requires data[]`);
    pages.push(Object.freeze({page,responseSha256:sha(text),responseText:text,payload}));
    const next=payload.pagination_key;
    if(!next)break;
    if(keys.has(next))throw new Error('J-Quants pagination key repeated');
    keys.add(next);paginationKey=next;
    if(page===maxPages)throw new Error('J-Quants pagination exceeded maxPages');
  }
  return Object.freeze({endpoint,normalizedQuery:Object.freeze(stable(query??{})),pages:Object.freeze(pages),pageCount:pages.length,aggregateSha256:sha(JSON.stringify(pages.map(x=>x.responseSha256)))});
}

export async function acquireFormalL0Session({plan,authorization,partition,sessionDate,apiKey,fetchImpl,requestBudget,now=new Date()}={}){
  const auth=assertRuntimeAcquisitionAuthorization({plan,authorization,partition});
  if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate??''))throw new Error('valid sessionDate is required');
  const entitlementEnd=Date.parse(plan?.storageManifest?.purgeDeadlinesJst?.DAILY_AND_MASTER_LIGHT??'');
  const requestedAt=now instanceof Date?now.getTime():Date.parse(String(now));
  if(!Number.isFinite(entitlementEnd)||!Number.isFinite(requestedAt))throw new Error('valid entitlement deadline and acquisition time are required');
  if(requestedAt>=entitlementEnd)throw new Error('Light entitlement ended; Daily/Master acquisition is prohibited');
  const daily=await fetchJquantsPages({endpoint:'/equities/bars/daily',query:{date:sessionDate},apiKey,fetchImpl,requestBudget});
  const master=await fetchJquantsPages({endpoint:'/equities/master',query:{date:sessionDate},apiKey,fetchImpl,requestBudget});
  return Object.freeze({schemaVersion:1,mode:'FORMAL_L0_DAILY_AND_DATED_MASTER_ONLY',sessionDate,partition,planSha256:auth.planSha256,privateCacheRoot:auth.privateCacheRoot,daily,master,minuteRequests:0,manifestSha256:sha(JSON.stringify({sessionDate,partition,daily:daily.aggregateSha256,master:master.aggregateSha256,planSha256:auth.planSha256}))});
}

export async function acquireFormalL0WarmupDaily({plan,authorization,sessionDate,apiKey,fetchImpl,requestBudget,now=new Date()}={}){
  const partition='DEVELOPMENT_A';
  const auth=assertRuntimeAcquisitionAuthorization({plan,authorization,partition});
  const warmup=plan?.l0Contract?.causalWarmup;
  if(warmup?.evaluationPartition!==false||warmup?.dailyRequests!==1||sessionDate!==warmup?.sessionDate)throw new Error('request is outside frozen L0 causal warmup contract');
  const entitlementEnd=Date.parse(plan?.storageManifest?.purgeDeadlinesJst?.DAILY_AND_MASTER_LIGHT??'');
  const requestedAt=now instanceof Date?now.getTime():Date.parse(String(now));
  if(!Number.isFinite(entitlementEnd)||!Number.isFinite(requestedAt)||requestedAt>=entitlementEnd)throw new Error('Light entitlement ended; warmup Daily acquisition is prohibited');
  const daily=await fetchJquantsPages({endpoint:'/equities/bars/daily',query:{date:sessionDate},apiKey,fetchImpl,requestBudget});
  return Object.freeze({schemaVersion:1,mode:'FORMAL_L0_CAUSAL_WARMUP_DAILY_ONLY',sessionDate,partition,evaluationPartition:false,planSha256:auth.planSha256,privateCacheRoot:auth.privateCacheRoot,daily,masterRequests:0,minuteRequests:0,manifestSha256:sha(JSON.stringify({sessionDate,partition,evaluationPartition:false,daily:daily.aggregateSha256,planSha256:auth.planSha256}))});
}

export default {fetchJquantsPages,acquireFormalL0Session,acquireFormalL0WarmupDaily};
