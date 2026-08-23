import fs from 'node:fs';
import path from 'node:path';
import { buildP25ResearchPaperScoreboard } from '../predict/paper/p25-research-paper-scoreboard.js';
import { P25_RESEARCH_COST_POLICY_V1, validateP25ResearchCostPolicy } from '../predict/paper/p25-research-cost-policy.js';

const arg=(name,fallback=null)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const statePath=arg('--state');
const outputPath=arg('--output','data/p25-paper/scoreboard.json');
if(!statePath){console.error('usage: node scripts/build_p25_research_paper_scoreboard.mjs --state <json> [--output <json>]');process.exit(2);}

try{
  validateP25ResearchCostPolicy(P25_RESEARCH_COST_POLICY_V1);
  const state=JSON.parse(fs.readFileSync(statePath,'utf8'));
  if(Number(state?.assumptions?.commissionPerFill)!==Number(P25_RESEARCH_COST_POLICY_V1.commissionPerFill))throw new Error('Paper state commission does not match predeclared cost policy');
  if(Number(state?.assumptions?.slippageBps)!==Number(P25_RESEARCH_COST_POLICY_V1.slippageBps))throw new Error('Paper state slippage does not match predeclared cost policy');
  const scoreboard=buildP25ResearchPaperScoreboard({state});
  const payload={
    schemaVersion:1,
    phase:'57.p25.3af.research-paper-scoreboard-cli',
    status:'P25_RESEARCH_PAPER_SCOREBOARD_WRITTEN',
    createdAt:new Date().toISOString(),
    costPolicy:P25_RESEARCH_COST_POLICY_V1,
    ...scoreboard,
  };
  fs.mkdirSync(path.dirname(outputPath),{recursive:true});
  const tmp=`${outputPath}.tmp-${process.pid}`;
  fs.writeFileSync(tmp,JSON.stringify(payload,null,2)+'\n','utf8');
  fs.renameSync(tmp,outputPath);
  console.log(JSON.stringify({status:payload.status,output:outputPath,completedSessionCount:payload.completedSessionCount,endingEquity:payload.endingEquity,cumulativeReturnPct:payload.cumulativeReturnPct,maximumDrawdownPct:payload.maximumDrawdownPct,killSwitchTripped:payload.killSwitchTripped,executable:payload.executable},null,2));
}catch(error){
  console.error(JSON.stringify({status:'BLOCKED_P25_RESEARCH_PAPER_SCOREBOARD',error:String(error?.message??error),executable:false},null,2));
  process.exit(1);
}
