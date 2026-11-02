/**
 * No.1.1 shadow-readiness diagnostic that MAY run while the independent
 * Chart50 RSS collector is active. NO Excel COM, NO MarketSpeed, NO RSS,
 * NO live broker, NO market data writes, NO models, NO order transmission.
 *
 * Reads already-saved, code-pinned full G1 run, daily PASS mask, Chart50 plan,
 * and previously staged 1M bars. NEVER turns an absent evidence document into
 * "EXTERNALLY_REVIEWED". Outputs counts/states only, never private symbols.
 *
 * Executable from a temporary folder:
 * node script.mjs --engine-root <repo research path>
 *                 --daily-run <private run> --mask <private json>
 *                 --chart <private json> --previous-stage <private json>
 *                 --settings <optional private settings json>
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
const err=code=>{throw Error('NO11_PARALLEL_'+code)};
const assert=(v,code)=>{if(!v)err(code)};
const sha=v=>createHash('sha256').update(v).digest('hex');
const absolute=(v,code)=>{
  assert(typeof v==='string'&&path.isAbsolute(v),code+'_ABSOLUTE_REQUIRED');
  return path.resolve(v);
};
const json=(filename,max=50_000_000)=>{
  filename=absolute(filename,'JSON');
  const stat=fs.lstatSync(filename);
  assert(stat.isFile()&&!stat.isSymbolicLink()&&stat.size>1&&stat.size<=max,'SOURCE_FILE_INVALID');
  return JSON.parse(fs.readFileSync(filename,'utf8').replace(/^\uFEFF/,''));
};
const directory=(filename)=>{
  filename=absolute(filename,'SOURCE_DIRECTORY');
  const st=fs.lstatSync(filename);
  assert(st.isDirectory()&&!st.isSymbolicLink(),'SOURCE_DIRECTORY_INVALID');
  return filename;
};
function options(argv){
  const allowed=new Set(['--engine-root','--daily-run','--mask','--chart','--previous-stage','--settings']);
  assert(argv.length%2===0,'ARGUMENT_COUNT');
  const o={};
  for(let i=0;i<argv.length;i+=2){
    assert(allowed.has(argv[i])&&!Object.hasOwn(o,argv[i])&&argv[i+1],'ARGUMENT_INVALID');
    o[argv[i]]=argv[i+1];
  }
  assert(['--engine-root','--daily-run','--mask','--chart','--previous-stage']
    .every(k=>o[k]),'REQUIRED_ARGUMENT_MISSING');
  return o;
}
function statusSetting(filename,date){
  if(!filename||!fs.existsSync(filename))return {
    status:'NOT_CONFIGURED', model:'NOT_PROVEN',
    master:'NOT_PROVEN', evidence:'NOT_PROVEN', fullShadow:false};
  const s=json(filename,100_000);
  assert(s.schemaId==='ARK_SHADOW_ONECLICK_SETTINGS_V1'&&
    s.orderTransmission===false,'SETTINGS_CONTRACT_INVALID');
  const find=k=>typeof s[k]==='string'&&path.isAbsolute(s[k])&&fs.existsSync(s[k]);
  const prepared=find('preparedConfigFile'),template=find('bootstrapTemplateFile');
  assert(!(prepared&&template),'TWO_CONFIG_MODES_CONFLICT');
  let model='NOT_PROVEN',master='NOT_PROVEN';
  if(prepared||template){
    const c=json(s[prepared?'preparedConfigFile':'bootstrapTemplateFile'],100_000);
    assert(c.schemaId==='ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1'&&
      c.sessionDate===date&&c.productionReady===false&&c.orderTransmission===false,
      'BOOTSTRAP_TEMPLATE_INVALID');
    model=typeof c.runtimeRoot==='string'&&fs.existsSync(c.runtimeRoot)&&
      typeof c.h235ModelRoot==='string'&&fs.existsSync(c.h235ModelRoot)&&
      typeof c.shadowAccountConfig==='string'&&fs.existsSync(c.shadowAccountConfig)
      ? 'FILES_PRESENT_NOT_LOADED':'MISSING_ASSETS';
    if(typeof c.datedMaster==='string'&&fs.existsSync(c.datedMaster)){
      const m=json(c.datedMaster,5_000_000);
      master=m.sessionDate===date&&m.productionReady===false&&m.orderTransmission===false
       ? 'PRESENT_NOT_INDEPENDENTLY_VERIFIED':'INVALID_OR_WRONG_DATE';
    }else master='MISSING';
  }
  const evidence=find('securityEvidenceFile')&&find('evidenceDocumentsDir')?
    'FILES_PRESENT_REVIEW_NOT_CERTIFIED':'MISSING_OR_UNCONFIRMED';
  return {status:prepared?'PREPARED_CONFIG_PRESENT_NOT_PREFLIGHTED':
    template?'BOOTSTRAP_TEMPLATE_PRESENT_NOT_PREFLIGHTED':'NOT_CONFIGURED',
    model,master,evidence,fullShadow:false};
}
export async function audit(argv){
  const opts=options(argv);
  const engine=directory(opts['--engine-root']);
  const run=directory(opts['--daily-run']);
  for(const name of [run,opts['--mask'],opts['--chart'],opts['--previous-stage']]){
    const privateLocation=path.resolve(name);
    assert(!privateLocation.startsWith(engine+path.sep)&&privateLocation!==engine,
      'PRIVATE_PATH_IN_ENGINE_TREE');
  }
  const full=json(path.join(run,'plan.json'),4_000_000);
  const {planId,...body}=full;
  const io=await import(pathToFileURL(path.join(engine,'tools/no11_rss_daily_trend_census.mjs')));
  const {makeObservedPassWatchMask}=await import(
    pathToFileURL(path.join(engine,'runtime/no11_observed_pass_watch_gate.mjs')));
  const {validateNo11Chart50Plan}=await import(
    pathToFileURL(path.join(engine,'runtime/no11_rss_chart_50_prescreen.mjs')));
  assert(full.schemaId==='ARK_NO11_RSS_DAILY_CENSUS_PLAN_V1'&&
    full.asOfSession==='2026-10-26'&&full.symbols.length===4328&&
    sha(JSON.stringify(body))===planId&&full.codeSha256===io.codeIdentity(),
    'FULL_G1_IMMUTABLE_PLAN_OR_CODE_CHANGED');
  const captures=io.loadCaptures(run,full);
  assert(captures.length===4328,'FULL_G1_CAPTURE_INCOMPLETE');
  const expected=makeObservedPassWatchMask(full,captures);
  const mask=json(opts['--mask'],4_000_000);
  assert(mask.schemaId===expected.schemaId&&mask.asOfSession===expected.asOfSession&&
    mask.planId===expected.planId&&mask.orderTransmission===false&&mask.shadowOnly===true&&
    JSON.stringify(mask.observedPassSymbols)===JSON.stringify(expected.observedPassSymbols)&&
    mask.observedPassCount===expected.observedPassCount,'PASS_MASK_NOT_PINNED_TO_SOURCE');
  const receipt=json(opts['--chart'],4_000_000);
  assert(receipt.schemaId==='ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1'&&
    receipt.orderTransmission===false&&receipt.productionReady===false&&
    receipt.chartPlan?.sessionDate==='2026-10-27','CHART_RECEIPT_CONTRACT_INVALID');
  const plan=receipt.chartPlan;
  validateNo11Chart50Plan({chartPlan:plan,mask,sessionDate:'2026-10-27'});
  const stage=json(opts['--previous-stage']);
  assert(stage.schemaId==='ARK_NO11_PREVIOUS_ARCHIVE_STAGE_V1'&&
    stage.sessionDate==='2026-10-27'&&stage.previousSession==='2026-10-26'&&
    stage.chartPlanSha256===plan.planSha256&&stage.productionReady===false&&
    stage.orderTransmission===false,'PREVIOUS_STAGE_MISMATCH');
  const picked=new Set(plan.selectorInputSymbols);
  const available=Object.keys(stage.symbols||{}),missing=Object.keys(stage.omittedSymbols||{});
  assert(available.length+missing.length===picked.size&&
    available.every(x=>picked.has(x))&&missing.every(x=>picked.has(x))&&
    new Set([...available,...missing]).size===picked.size,
    'PREVIOUS_COVERAGE_MEMBERSHIP_MISMATCH');
  const s=statusSetting(opts['--settings'],'2026-10-27');
  const result={
    fullMarket:{status:'COMPLETE_PINNED',count:captures.length,observedG1Pass:mask.observedPassCount},
    chart:{status:'PRESCREEN_VALIDATED_NOT_LIVE_CAPACITY_CERTIFIED',
      selected:plan.selectorInputSymbols.length,charts:plan.arkChartsUsed,
      reserve:plan.reserveEmptyChartSlots,
      protectedAccountPositionsVerified:false},
    previous:{status:'STAGED_ONLY_NO_DATED_MASTER',usable:available.length,missing:missing.length},
    settings:s,
    shadowIntegratedPreflight:'NOT_PASSED',canLaunchFullShadow:false,
    excelTouched:false,marketSpeedTouched:false,
    brokerTouched:false,orderTransmission:false
  };
  return result;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
  try {
    const r=await audit(process.argv.slice(2));
    console.log('NO11_PARALLEL_AUDIT_FULL_G1='+r.fullMarket.count+'/'+4328+'|PASS='+r.fullMarket.observedG1Pass);
    console.log('NO11_PARALLEL_AUDIT_CHART='+r.chart.selected+'/50|EMPTY_RESERVE='+r.chart.reserve);
    console.log('NO11_PARALLEL_AUDIT_PREVIOUS='+r.previous.usable+'|MISSING='+r.previous.missing);
    console.log('NO11_PARALLEL_AUDIT_SHADOW_SETTINGS='+r.settings.status);
    console.log('NO11_PARALLEL_AUDIT_MODEL_ASSETS='+r.settings.model);
    console.log('NO11_PARALLEL_AUDIT_DATED_MASTER='+r.settings.master);
    console.log('NO11_PARALLEL_AUDIT_EXTERNAL_REVIEW='+r.settings.evidence);
    console.log('NO11_PARALLEL_AUDIT_INTEGRATED_PREFLIGHT=NOT_PASSED');
    console.log('NO11_PARALLEL_AUDIT_OPERATION=DISK_READONLY_NO_EXCEL');
    console.log('ORDER_TRANSMISSION=False');
  } catch(e) {
    console.log('NO11_PARALLEL_AUDIT=BLOCKED|'+(
      /^NO11_PARALLEL_[A-Z0-9_]+$/.test(String(e.message))?
      e.message:'NO11_PARALLEL_SOURCE_OR_PRIVATE_INPUT_UNAVAILABLE'));
    console.log('ORDER_TRANSMISSION=False');
    process.exitCode=2;
  }
}
