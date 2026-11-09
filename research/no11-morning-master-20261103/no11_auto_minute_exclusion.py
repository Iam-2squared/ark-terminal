#!/usr/bin/env python3
"""Exclude a few *verified* defective previous-minute inputs automatically.

No market recapture, invented prices, broker/order calls, unsafely broad
fallback, unverified changes to LIVE positions, or original-receipt edits.

Automatic on every post-close DATA stage, including Friday->Monday catch-up.
A known small number of bad 1M sources is removed from entry eligibility;
other selected sources keep their original physical RSS receipts and hashes.
A protected/held/watch/pending symbol must NEVER be dropped automatically.
All replacement plans and inputs are native-validated before publication.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

MARK='ARK_NO11_AUTOMATIC_BAD_1M_SYMBOL_EXCLUSION_V1'
CAPTURE_SCHEMA='ARK_NO11_RSS_TRAINING_CAPTURE_PROGRESS_V1'
STAGE_SCHEMA='ARK_NO11_PREVIOUS_ARCHIVE_STAGE_V1'
CHART_SCHEMA='ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1'
SYMBOL=re.compile(r'^[0-9A-Z]{4}\.T$')
SHA=re.compile(r'^[a-f0-9]{64}$')
FILE=re.compile(r'^\d{5}-[0-9A-Z]{4}_T-1M\.json$')
GOOD='OBSERVED_ARCHIVE_NOT_TRAINING_CERTIFIED'
MAX_FAILED=3  # 47 -> at most 3; never broaden to a partly unknown universe.

def need(value,reason):
    if not value:
        raise ValueError('NO11_AUTO_MINUTE_EXCLUSION_'+reason)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def encode(obj):
    return (json.dumps(obj,ensure_ascii=False,separators=(',',':'),
                       allow_nan=False)+'\n').encode('utf-8')

def read_json(m,p):
    data,raw=m.read(p)
    need(type(data) is dict,'SOURCE_OBJECT_REQUIRED')
    return data,raw

def save_once(m,path,raw):
    # No overwrites even after an interrupted write. OS hard-link publishes
    # complete source bytes atomically and avoids corrupting old receipts.
    path=Path(path)
    m.safe(path.parent,directory=True)
    need(not path.is_symlink(),'OUTPUT_REPARSE')
    if path.exists():
        need(path.read_bytes()==raw,'IMMUTABLE_OUTPUT_CHANGED')
        return path
    tmp=None
    try:
        with tempfile.NamedTemporaryFile('wb',dir=path.parent,
                prefix='.auto-minutes-',delete=False) as fp:
            tmp=Path(fp.name)
            fp.write(raw)
            fp.flush()
            os.fsync(fp.fileno())
        try:
            os.link(tmp,path)
        except FileExistsError:
            need(m.safe(path).read_bytes()==raw,'CONCURRENT_OUTPUT_CHANGED')
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
    return m.safe(path)

def hardlink_member(m,source,target,sha):
    # Compatibility name only: V2 writes an independent byte-identical copy.
    # An edit to a derived receipt can never alter the original source inode.
    raw=m.safe(source).read_bytes()
    need(digest(raw)==sha,'ORIGINAL_1M_RECEIPT_HASH')
    return save_once(m,Path(target),raw)

NODE=r"""import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
const [modulePath,chartPath,maskPath]=process.argv.slice(2);
const {validateNo11Chart50Plan}=await import(pathToFileURL(modulePath).href);
const hash=data=>createHash('sha256').update(data).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const source=read(chartPath),mask=read(maskPath);
const request=JSON.parse(fs.readFileSync(0,'utf8'));
const fail=(ok,code)=>{if(!ok)throw Error('NO11_AUTO_MINUTE_EXCLUSION_'+code)};
fail(source.schemaId==='ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1' &&
 source.productionReady===false&&source.orderTransmission===false,'RECEIPT_UNSAFE');
const old=source.chartPlan;
const selected=validateNo11Chart50Plan({chartPlan:old,mask,sessionDate:old.sessionDate});
const removed=request.removed;
const rm=new Set(removed);
fail(Array.isArray(removed)&&removed.length>0&&removed.length<=3&&
 rm.size===removed.length&&removed.every(x=>selected.includes(x)),'SCOPE');
const protectedSet=new Set(old.protectedChartSymbols);
for(const key of ['heldSymbols','activeWatchSymbols','pendingOrderSymbols']){
 fail(Array.isArray(old[key])&&old[key].every(x=>typeof x==='string'),'PROTECTED_FORMAT');
 for(const x of old[key])protectedSet.add(x);
}
fail(!removed.some(x=>protectedSet.has(x)),'PROTECTED_SYMBOL_CANNOT_BE_DROPPED');
const kept=selected.filter(x=>!rm.has(x));
fail(kept.length===request.kept.length&&JSON.stringify(kept)===JSON.stringify(request.kept),
 'SELECTED_ORDER');
const {planSha256,...body}=structuredClone(old);
body.selectorInputSymbols=kept;
body.scanChartSymbols=old.scanChartSymbols.filter(x=>!rm.has(x));
body.allRequestedChartSymbols=old.allRequestedChartSymbols.filter(x=>!rm.has(x));
body.arkChartsUsed=body.allRequestedChartSymbols.length;
body.totalChartFunctionsBudgeted=body.arkChartsUsed+body.occupiedByOtherChartFunctions;
body.g1UnscannedCount=mask.observedPassSymbols.length-kept.length;
if(body.entryUniverseMode!==undefined){
 body.reviewedEntrySymbols=old.reviewedEntrySymbols.filter(x=>!rm.has(x));
 body.unreviewedG1SymbolsExcludedFromEntry=
    mask.observedPassSymbols.length-body.reviewedEntrySymbols.length;
 fail(body.reviewedEntrySymbols.length>0,'NO_REVIEWED_ENTRIES_LEFT');
}
body.automaticInvalidMinuteExclusion={
 schemaId:'ARK_NO11_AUTOMATIC_BAD_1M_ENTRY_EXCLUSION_V1',
 parentChartPlanSha256:planSha256,
 parentPreviousArchiveStageSha256:request.parentStageSha,
 parentProgressSha256:request.parentProgressSha,
 excludedSymbols:removed,
 originalSelectedCount:selected.length,
 retainedSelectedCount:kept.length,
 liveOrExitProtectedSymbolsDropped:false,
 noReranking:true,sourceBarsReusedWithoutModification:true,
 productionReady:false,orderTransmission:false
};
const updated={...body,planSha256:hash(JSON.stringify(body))};
fail(JSON.stringify(validateNo11Chart50Plan({
 chartPlan:updated,mask,sessionDate:old.sessionDate}))===JSON.stringify(kept),
 'NATIVE_REVALIDATION_FAILED');
const receipt={...source,chartPlan:updated,
 automaticInvalidMinuteExclusionApplied:true,
 originalChartReceiptSha256:request.originalChartSha,
 originalPreviousArchiveStageSha256:request.parentStageSha};
console.log(JSON.stringify(receipt));
"""

def native_chart(m,record,engine,removed,kept,stage_sha,progress_sha):
    chart_path=m.safe(record['chart'])
    native=m.safe(Path(engine)/'runtime/no11_rss_chart_50_prescreen.mjs')
    request={
        'removed':removed,'kept':kept,'parentStageSha':stage_sha,
        'parentProgressSha':progress_sha,'originalChartSha':digest(chart_path.read_bytes())}
    # Never execute a dynamically supplied script; NODE is a fixed source
    # checked by the installed data-bound helper SHA.
    # Process.argv for node --input-type=module -: [node,'-',native,chart,mask]
    with tempfile.TemporaryDirectory(prefix='ark-auto-minute-native-') as directory:
        payload=Path(directory)/'request.json'
        payload.write_bytes(encode(request))
        script=NODE.replace("JSON.parse(fs.readFileSync(0,'utf8'))",
                           "JSON.parse(fs.readFileSync(process.argv[5],'utf8'))")
        argv=['node','--input-type=module','-',str(native),
              str(chart_path),str(record['mask']),str(payload)]
        res=subprocess.run(argv,input=script.encode('utf-8'),capture_output=True,
                           timeout=45,check=False)
    need(res.returncode==0,'NATIVE_CHART_VALIDATION_FAILED')
    raw=res.stdout
    need(0<len(raw)<2_000_000 and raw.count(b'\n')==1,
         'NATIVE_CHART_SINGLE_OUTPUT')
    try:
        data=json.loads(raw)
    except (TypeError,ValueError):
        need(False,'NATIVE_CHART_RESPONSE')
    need(data.get('schemaId')==CHART_SCHEMA and
         data.get('chartPlan',{}).get('selectorInputSymbols')==kept
         and data.get('productionReady') is False
         and data.get('orderTransmission') is False,
         'NATIVE_CHART_SCOPE_CHANGED')
    return data,raw

def prune(m,record,root,binding,previous_checkpoint):
    record=dict(record)
    root=m.safe(root,directory=True)
    stage_file=m.safe(record['stage'])
    chart_file=m.safe(record['chart'])
    mask_file=m.safe(record['mask'])
    stage,sb=read_json(m,stage_file)
    chart,cb=read_json(m,chart_file)
    mask,mb=read_json(m,mask_file)
    m.verify_receipt(stage_file,sb,'previous-archive-stage',64)
    m.verify_receipt(chart_file,cb,'no11-chart50-private',16)
    m.verify_receipt(mask_file,mb,'no11-observed-pass-watch',16)
    need(stage.get('schemaId')==STAGE_SCHEMA and
         stage.get('orderTransmission') is False
         and stage.get('productionReady') is False,
         'PREVIOUS_STAGE_UNSAFE')
    selected=chart.get('chartPlan',{}).get('selectorInputSymbols')
    symbols=stage.get('symbols')
    omitted=stage.get('omittedSymbols')
    need(type(selected) is list and 1<=len(selected)<=47 and
         type(symbols) is dict and type(omitted) is dict,
         'SOURCE_SCOPE_INVALID')
    need(stage.get('selectedSymbols')==selected and
         stage.get('sessionDate')==record['sessionDate'] and
         stage.get('previousSession')==record['previousSession'] and
         stage.get('chartPlanSha256')==chart['chartPlan']['planSha256'],
         'STAGE_CHART_DATES_OR_IDENTITY')
    if not omitted:
        return record
    need(all(type(x) is str and SYMBOL.fullmatch(x)
             and type(y) is str and 0<len(y)<=160 for x,y in omitted.items()),
         'OMITTED_FORMAT')
    dropped=[s for s in selected if s in omitted]
    keep=[s for s in selected if s not in omitted]
    need(set(dropped)==set(omitted) and set(keep)==set(symbols) and
         len(dropped)<=MAX_FAILED and
         len(dropped)<=max(1,len(selected)//10) and len(keep)>=1,
         'TOO_MANY_OR_AMBIGUOUS_BAD_SYMBOLS')
    # Explicitly protected held/watch/pending names never auto-excluded.
    protected=set()
    plan=chart['chartPlan']
    for key in ('protectedChartSymbols','heldSymbols',
                'activeWatchSymbols','pendingOrderSymbols'):
        values=plan.get(key)
        need(type(values) is list,'PROTECTED_SCOPE_MISSING')
        protected.update(values)
    need(not protected.intersection(dropped),'PROTECTED_HOLDING_EXIT_CONTEXT')
    source_capture=m.safe(record['capture'],directory=True)
    capture_root,checkpoint,progress_sha=previous_checkpoint(source_capture)
    need(checkpoint.get('schemaId')==CAPTURE_SCHEMA and
         checkpoint.get('completed')==len(selected) and
         checkpoint.get('requested')==len(selected) and
         stage.get('progressSha256')==progress_sha and
         checkpoint.get('productionReady') is False and
         checkpoint.get('orderTransmission') is False,
         'ORIGINAL_MINUTE_CHECKPOINT_INCOMPLETE')
    files=checkpoint.get('files')
    need(type(files) is list and len(files)==len(selected),'CHECKPOINT_FILES')
    by_symbol={}
    for row in files:
        need(type(row) is dict,'CHECKPOINT_MEMBER')
        symbol=row.get('symbol')
        filename=row.get('file')
        sha=row.get('sha256')
        need(type(symbol) is str and SYMBOL.fullmatch(symbol) and
             type(filename) is str and FILE.fullmatch(filename) and
             filename.endswith('-'+symbol.replace('.','_')+'-1M.json') and
             type(sha) is str and SHA.fullmatch(sha) and
             symbol not in by_symbol,'CHECKPOINT_MEMBER_CONTRACT')
        need(digest(m.safe(capture_root/filename).read_bytes())==sha,
             'CHECKPOINT_MEMBER_HASH_CHANGED')
        by_symbol[symbol]=row
    need(set(by_symbol)==set(selected),'CHECKPOINT_SYMBOL_UNIVERSE')
    for code in keep:
        member=by_symbol[code]
        stage_member=symbols[code]
        need(type(stage_member) is dict and
             stage_member.get('originalArchiveSha256')==member['sha256'] and
             member.get('status')==GOOD and
             type(member.get('rows')) is int and member['rows']>=2,
             'KEEP_MEMBER_NOT_PROVEN_USABLE')
    report={
      'schemaId':'ARK_NO11_AUTO_MINUTE_EXCLUSION_EVIDENCE_V1',
      'independentSourceCopiesVersion':2,
      'sessionDate':record['sessionDate'],
      'previousSession':record['previousSession'],
      'parentChartReceiptSha256':digest(cb),
      'parentArchiveStageSha256':digest(sb),
      'parentMinuteProgressSha256':progress_sha,
      'originalSelectedSymbols':selected,'keptSymbols':keep,
      'omittedReasons':{code:omitted[code] for code in dropped},
      'noReranking':True,'noPriceOrSourceModification':True,
      'protectedExitContextPreserved':True,
      'productionReady':False,'orderTransmission':False}
    marker=digest(encode(report))[:24]
    target=root/'auto-minute-exclusions'/record['sessionDate']/marker
    target.mkdir(parents=True,exist_ok=True)
    target=m.safe(target,directory=True)
    evidence=m.immutable(target,'bad-minute-exclusion-evidence',report)
    checked=[by_symbol[s] for s in selected if s in set(keep)]
    for member in checked:
        hardlink_member(m,capture_root/member['file'],
                        target/member['file'],member['sha256'])
    subset=deepcopy(checkpoint)
    subset['files']=checked
    subset['requested']=len(keep)
    subset['completed']=len(keep)
    subset['observedSymbols']=len(keep)
    subset['unavailableSymbols']=0
    subset['rows']=sum(row['rows'] for row in checked)
    subset['originalProgressSha256']=progress_sha
    subset['automaticMinuteExclusionEvidenceSha256']=digest(evidence.read_bytes())
    progress_path=save_once(m,target/('progress-%05d.json'%len(keep)),
                            encode(subset))
    need(progress_path.name=='progress-%05d.json'%len(keep),
         'NEW_CHECKPOINT_NAME')
    chart_record,chart_raw=native_chart(m,record,binding['engine'],dropped,keep,digest(sb),progress_sha)
    # New *chart* must live next to unchanged original mask and refresh-run
    # because the existing pinned MASTER expects all 3 in the same directory.
    run=m.safe(record['run'],directory=True)
    need(chart_file.parent==mask_file.parent==run,
         'CHART_AND_MASK_ORIGINAL_PARENT')
    newchart=save_once(m,run/('no11-chart50-private-'+digest(chart_raw)[:16]+'.json'),
                       chart_raw)
    stage_new=deepcopy(stage)
    stage_new['selectedSymbols']=keep
    stage_new['symbols']={code:symbols[code] for code in keep}
    stage_new['omittedSymbols']={}
    stage_new['chartPlanSha256']=chart_record['chartPlan']['planSha256']
    stage_new['progressSha256']=digest(progress_path.read_bytes())
    stage_new['originalUnfilteredPreviousStageSha256']=digest(sb)
    stage_new['automaticMinuteExclusionEvidenceSha256']=digest(evidence.read_bytes())
    stage_new['noMissingEntryArchiveClaimed']=True
    newstage=m.immutable(target,'previous-archive-stage',stage_new)
    newrecord=dict(record)
    newrecord.update(chart=str(newchart),stage=str(newstage),capture=str(target))
    # Always run the unchanged native chart and morning scope validators; the
    # self-generated proof is not enough to publish a next-session handoff.
    need(m.native_scope(binding['engine'],newchart,mask_file)==keep,
         'PINNED_NATIVE_CHART_SCOPE_MISMATCH')
    checked,_=m.validate_scope({'sessionDate':record['sessionDate']},
                               chart_record,mask,stage_new)
    need(checked==keep,'PINNED_MORNING_SELECTED_SCOPE_MISMATCH')
    print('NO11_AUTO_MINUTE_EXCLUDED='+str(len(dropped))+'/'+str(len(selected)))
    print('NO11_AUTO_MINUTE_RETAINED='+str(len(keep)))
    print('NO11_AUTO_MINUTE_EXCLUSION_POLICY=SMALL_VERIFIED_ENTRY_ONLY')
    print('NO11_AUTO_MINUTE_ORIGINAL_RECEIPTS_PRESERVED=True')
    print('NO11_AUTO_MINUTE_EXIT_HOLDING_UNTOUCHED=True')
    print('ORDER_TRANSMISSION=False')
    return newrecord
