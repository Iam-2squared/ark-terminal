import fs from 'node:fs';
import path from 'node:path';
import { replayP25ResearchSignals } from '../predict/paper/p25-offline-paper-replay.js';
import { createResearchPaperLedger, appendResearchPaperSession, verifyResearchPaperLedger } from '../predict/paper/p25-research-paper-ledger.js';
import { buildP25PaperShadowReport } from '../predict/shadow/p25-paper-shadow-report.js';
import { evaluateP25PaperKillSwitch } from '../predict/shadow/p25-paper-kill-switch.js';
import { P25_SIGNAL_INTENT_SAFETY } from '../predict/paper/p25-signal-intent-adapter.js';

const arg=(name,fallback=null)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const load=file=>JSON.parse(fs.readFileSync(file,'utf8'));
const write=(file,value)=>{fs.mkdirSync(path.dirname(file),{recursive:true});const tmp=`${file}.tmp-${process.pid}`;fs.writeFileSync(tmp,JSON.stringify(value,null,2)+'\n');fs.renameSync(tmp,file);};

const exportPath=arg('--paper-export');
const statePath=arg('--state');
const outputPath=arg('--output','data/p25-paper-state.json');
const shadowPath=arg('--shadow-observations');
const quantity=Number(arg('--quantity','100'));
const commissionPerFill=Number(arg('--commission-per-fill','0'));
const slippageBps=Number(arg('--slippage-bps','0'));
if(!exportPath){console.error('usage: node scripts/run_p25_research_paper_daily.mjs --paper-export <json> [--state <json>] [--shadow-observations <json>] [--output <json>]');process.exit(2);}

try{
  for(const [key,value] of Object.entries(P25_SIGNAL_INTENT_SAFETY))if(value!==false)throw new Error(`unsafe flag ${key}`);
  const exported=load(exportPath);
  if(exported?.mode!=='research_offline_only'||exported?.executable!==false||!Array.isArray(exported?.sessions))throw new Error('valid research-only Paper export required');
  const previous=statePath&&fs.existsSync(statePath)?load(statePath):null;
  let account=previous?.account??null;
  let ledger=previous?.ledger??createResearchPaperLedger({initialCash:Number(account?.initialCash??1_000_000)});
  if(!verifyResearchPaperLedger(ledger))throw new Error('existing research Paper ledger integrity failure');
  const processed=new Set(ledger.sessions.map(row=>row.sessionDate));
  const shadowObservations=shadowPath&&fs.existsSync(shadowPath)?load(shadowPath):null;
  const reports=[];

  for(const session of exported.sessions){
    const sessionDate=String(session?.sessionDate??'');
    if(processed.has(sessionDate))continue;
    const rows=session?.input?.rows;
    if(!Array.isArray(rows))throw new Error(`Paper input rows missing for ${sessionDate}`);
    const replay=replayP25ResearchSignals({signals:rows,startingAccount:account,initialCash:Number(account?.initialCash??1_000_000),quantity,commissionPerFill,slippageBps});
    account=replay.account;
    const observations=shadowObservations?.[sessionDate]??null;
    const shadowReport=observations?buildP25PaperShadowReport({replayResult:replay,observations}):null;
    const killSwitch=evaluateP25PaperKillSwitch({account,shadowReport,safety:P25_SIGNAL_INTENT_SAFETY});
    ledger=appendResearchPaperSession({ledger,sessionDate,replayResult:replay,sourceEvaluationSha256:session?.sourceEvaluationSha256??null});
    if(!verifyResearchPaperLedger(ledger))throw new Error('research Paper ledger integrity failure after append');
    reports.push({sessionDate,replayEventCount:replay.events.length,shadowReport,killSwitch});
    if(killSwitch.tripped)break;
  }

  const payload={
    schemaVersion:1,
    phase:'57.p25.3ab.daily-research-paper-runner',
    status:'P25_RESEARCH_PAPER_STATE_WRITTEN',
    createdAt:new Date().toISOString(),
    mode:'research_offline_only',
    executable:false,
    sourceLineageManifestHeadSha256:exported.lineageManifestHeadSha256??null,
    assumptions:{quantity,commissionPerFill,slippageBps},
    completedSessionCount:ledger.sessions.length,
    account,
    ledger,
    reports,
    methodology:{prospectiveScoringUnchanged:true,currentOuterOosDoesNotSelectDynamicN:true,futureBarsUsedForSignalGeneration:false,freshHoldoutConsumed:false,shadowOptionalUntilObservationFeedExists:true},
    safety:P25_SIGNAL_INTENT_SAFETY,
  };
  write(outputPath,payload);
  console.log(JSON.stringify({status:payload.status,output:outputPath,completedSessionCount:payload.completedSessionCount,equity:account?.equity??null,killSwitchTripped:reports.some(x=>x.killSwitch?.tripped===true),safety:P25_SIGNAL_INTENT_SAFETY},null,2));
}catch(error){
  console.error(JSON.stringify({status:'BLOCKED_P25_RESEARCH_PAPER_DAILY',error:String(error?.message??error),safety:P25_SIGNAL_INTENT_SAFETY},null,2));
  process.exit(1);
}
