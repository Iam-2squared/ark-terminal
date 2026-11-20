import fs from 'node:fs';
import {createHash} from 'node:crypto';

const read=url=>JSON.parse(fs.readFileSync(url,'utf8'));
export const V2_DEVELOPMENT=Object.freeze(read(new URL('./phase57-long-only-v2-development-sessions.json',import.meta.url)));
export const V2_COMPARISON_CONTRACT=Object.freeze(read(new URL('./phase57-long-only-v2-comparison-contract.json',import.meta.url)));
export const V2_PREACQUISITION_AUDIT=Object.freeze(read(new URL('./phase57-long-only-v2-preacquisition-audit.json',import.meta.url)));
const hash=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');

export function assertV2PreFitContract({allocation,l1Contract,l2Contract}={}){
  if(hash(V2_DEVELOPMENT.sessions)!==V2_DEVELOPMENT.sessionListSha256)throw new Error('v2 session SHA mismatch');
  const expected=[...allocation.partitions.DEVELOPMENT_A.slice(-5),...allocation.partitions.DEVELOPMENT_B];
  if(JSON.stringify(expected)!==JSON.stringify(V2_DEVELOPMENT.sessions))throw new Error('v2 sessions are not allocation-v3 A-tail5+B');
  for(const observed of [...l1Contract.sessions,...l2Contract.sessions])if(V2_DEVELOPMENT.sessions.includes(observed))throw new Error(`v2 session already has approved Minute outcome: ${observed}`);
  if(V2_PREACQUISITION_AUDIT.mechanicalResults.approvalConditionPassed!==true)throw new Error('v2 acquisition audit did not pass');
  const c=V2_COMPARISON_CONTRACT;
  if(c.familyCount!==1||c.hyperparameterCandidates.length<4||c.hyperparameterCandidates.length>8)throw new Error('v2 family/grid contract violation');
  if(c.target.horizonBars!==6||c.target.barMinutes!==5||Math.max(...c.hyperparameterCandidates.map(x=>x.maxDepth))>3)throw new Error('v2 horizon/complexity contract violation');
  if(c.featureUniverse.length!==15||c.topN.join(',')!=='1,3,5,10,20,30,50')throw new Error('v2 feature/selection contract changed');
  return true;
}

export default {V2_DEVELOPMENT,V2_COMPARISON_CONTRACT,V2_PREACQUISITION_AUDIT,assertV2PreFitContract};
