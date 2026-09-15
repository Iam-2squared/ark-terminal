import fs from 'node:fs';
import {buildAcquisitionGateSummary} from '../predict/long-only/phase57-long-only-acquisition-gate.js';

const plan=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-data-plan.json',import.meta.url),'utf8'));
const allocation=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-session-allocation-v3.json',import.meta.url),'utf8'));
const credentialPresent=Boolean(process.env.JQUANTS_API_KEY);
const privateCacheRootConfirmed=Boolean(process.env.PHASE57_LONG_ONLY_PRIVATE_CACHE_ROOT);
const purgeDryRunPassed=process.env.PHASE57_LONG_ONLY_PURGE_DRY_RUN_PASSED==='true';
console.log(JSON.stringify(buildAcquisitionGateSummary({plan,allocation,credentialPresent,privateCacheRootConfirmed,purgeDryRunPassed}),null,2));
