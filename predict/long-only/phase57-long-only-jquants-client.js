import {createHash} from 'node:crypto';
import {assertRuntimeAcquisitionAuthorization} from './phase57-long-only-acquisition-gate.js';

const API_ROOT='https://api.jquants.com/v2';
const sha=value=>createHash('sha256').update(value).digest('hex');
const stable=value=>value&&typeof value==='object'?(Array.isArray(value)?value.map(stable):Object.fromEntries(Object.keys(value).sort().map(k=>[k,stable(value[k])]))):value;

export async function fetchJquantsPages({endpoint,query,apiKey,fetchImpl=globalThis.fetch,maxPages=100}={}){
  if(!['/equities/bars/daily','/equities/master','/equities/bars/minute'].includes(endpoint))throw new Error('endpoint is outside frozen J-Quants contract');
  if(!apiKey||typeof fetchImpl!=='function')throw new Error('API key and fetch implementation are required');
  const pages=[],keys=new Set();let paginationKey;
  for(let page=1;page<=maxPages;page++){
    const params=new URLSearchParams(Object.entries(query??{}).map(([k,v])=>[k,String(v)]));
    if(paginationKey)params.set('pagination_key',paginationKey);
    const response=await fetchImpl(`${API_ROOT}${endpoint}?${params}`,{headers:{'x-api-key':apiKey}});
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

export async function acquireFormalL0Session({plan,authorization,partition,sessionDate,apiKey,fetchImpl}={}){
  const auth=assertRuntimeAcquisitionAuthorization({plan,authorization,partition});
  if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate??''))throw new Error('valid sessionDate is required');
  const daily=await fetchJquantsPages({endpoint:'/equities/bars/daily',query:{date:sessionDate},apiKey,fetchImpl});
  const master=await fetchJquantsPages({endpoint:'/equities/master',query:{date:sessionDate},apiKey,fetchImpl});
  return Object.freeze({schemaVersion:1,mode:'FORMAL_L0_DAILY_AND_DATED_MASTER_ONLY',sessionDate,partition,planSha256:auth.planSha256,privateCacheRoot:auth.privateCacheRoot,daily,master,minuteRequests:0,manifestSha256:sha(JSON.stringify({sessionDate,partition,daily:daily.aggregateSha256,master:master.aggregateSha256,planSha256:auth.planSha256}))});
}

export default {fetchJquantsPages,acquireFormalL0Session};
