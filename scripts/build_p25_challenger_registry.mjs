import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {P25_EXIT_V4_POLICY,P25_EXIT_V4_POLICY_SHA256,P25_EXIT_V4_SAFETY} from '../predict/daytrade/phase57-p25-exit-v4-structural-risk.js';
import {PHASE57_INTRADAY_UNIVERSE_V2_POLICY,PHASE57_INTRADAY_UNIVERSE_V2_SAFETY} from '../predict/daytrade/phase57-p25-intraday-dynamic-universe-v2.js';

const output=process.argv[2]??'tmp/p25-challenger-registry.json';
const canonical=v=>JSON.stringify(v);
const v2PolicySha256=crypto.createHash('sha256').update(canonical(PHASE57_INTRADAY_UNIVERSE_V2_POLICY)).digest('hex');
const required=['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'];
for(const [name,safety] of [['EXIT_V4',P25_EXIT_V4_SAFETY],['DYNAMIC5M_V2',PHASE57_INTRADAY_UNIVERSE_V2_SAFETY]])for(const k of required)if(safety?.[k]!==false)throw new Error(`${name} unsafe ${k}`);
const payload={schemaVersion:1,phase:'57.p25.challenger-registry',status:'P25_CHALLENGER_REGISTRY_FROZEN',createdAt:new Date().toISOString(),challengers:{EXIT_V4:{policy:P25_EXIT_V4_POLICY,policySha256:P25_EXIT_V4_POLICY_SHA256,firstFreshEligibleDate:P25_EXIT_V4_POLICY.firstFreshEligibleDate,safety:P25_EXIT_V4_SAFETY},DYNAMIC5M_V2:{policy:PHASE57_INTRADAY_UNIVERSE_V2_POLICY,policySha256:v2PolicySha256,firstFreshEligibleDate:PHASE57_INTRADAY_UNIVERSE_V2_POLICY.firstFreshEligibleDate,safety:PHASE57_INTRADAY_UNIVERSE_V2_SAFETY}},methodology:{august31FailureAnalysisOnly:true,resultBasedRetuning:false,postHocWinnerFiltering:false,appendOnlyPersistence:true,baselineV3AndDynamic5mV1Untouched:true}};
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(payload,null,2)+'\n');
console.log(JSON.stringify({status:payload.status,exitV4Sha:P25_EXIT_V4_POLICY_SHA256,dynamic5mV2Sha:v2PolicySha256},null,2));
