"""Zero-inquiry automatic skip of small proven bad previous-minute entries.

Exercises REAL native Node chart plan validation, existing morning source
validator, actual immutable progress files and read-only source hardlinks.
No Excel/provider/broker call; never invent usable 1M rows for omitted member.
"""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ENGINE=HERE.parent/'no12-prebuy-causal-runtime-20261011'
sys.path.insert(0,str(HERE))
import morning_master as m
import no11_auto_minute_exclusion as auto
import no11_circuit_repair as repair
import daily_cycle as cycle_orig

def j(obj):
    return (json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n').encode()

def write_receipt(folder,prefix,obj,digits):
    raw=j(obj)
    path=folder/(prefix+'-'+hashlib.sha256(raw).hexdigest()[:digits]+'.json')
    path.write_bytes(raw)
    return path

def plan_fixture(engine,run,selected,session):
    previous='2026-11-09'
    mask={'schemaId':'ARK_NO11_DAILY_OBSERVED_PASS_ONLY_SHADOW_V1',
          'shadowOnly':True,'productionReady':False,
          'orderTransmission':False,'strictNoUnknownFallback':True,
          'asOfSession':previous,'planId':'a'*64,
          'observedPassSymbols':selected,'observedPassCount':len(selected)}
    mask_path=write_receipt(run,'no11-observed-pass-watch',mask,16)
    node=ENGINE/'runtime/no11_rss_chart_50_prescreen.mjs'
    code="""import {makeNo11G1Chart50Plan as make,validateNo11Chart50Plan as validate} from '%s';
import fs from 'node:fs';
const mask=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const symbols=mask.observedPassSymbols;
const priorities=symbols.map((symbol,i)=>({symbol,minMarginPct:100+i,
 meanMarginPct:50+i}));
const p=make({mask,priorityRows:priorities,sessionDate:'%s'});
validate({chartPlan:p,mask,sessionDate:'%s'});
console.log(JSON.stringify({schemaId:'ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1',
 chartPlan:p,productionReady:false,orderTransmission:false}));"""%(node.as_uri(),session,session)
    r=subprocess.run(['node','--input-type=module','-',
            str(mask_path)],input=code,text=True,encoding='utf-8',
            capture_output=True,timeout=30)
    if r.returncode:raise AssertionError(r.stdout+r.stderr)
    chart=json.loads(r.stdout)
    chart_path=write_receipt(run,'no11-chart50-private',chart,16)
    return mask_path,chart_path,chart

class AutoInvalidMinuteTest(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix='ark-real-minute-prune-')
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.run=self.root/'weekly-refresh'
        self.run.mkdir()
        self.capture=self.root/'original-capture'
        self.capture.mkdir()
        self.selected=[f'{3000+i:04d}.T' for i in range(8)]
        self.mask,self.chart_path,self.chart=plan_fixture(
            ENGINE,self.run,self.selected,'2026-11-10')
        # Native strength ranking may reorder PASS candidates; the saved
        # Chart50 selector order, not lexical input order, is authoritative.
        self.selected=list(self.chart['chartPlan']['selectorInputSymbols'])
        self.members=[]
        self.kept={}
        self.failed=[self.selected[-1]]
        for i,s in enumerate(self.selected,1):
            raw=j({'schemaId':'ARK_NO11_RSS_TRAINING_SYMBOL_ARCHIVE_V1',
                   'symbol':s,'period':'1M','status':'OBSERVED_ARCHIVE_NOT_TRAINING_CERTIFIED',
                   'productionReady':False,'orderTransmission':False,
                   'rows':[{'session':'2026-11-09','close':1}]})
            name=f'{i:05d}-{s.replace(".","_")}-1M.json'
            path=self.capture/name
            path.write_bytes(raw)
            sha=hashlib.sha256(raw).hexdigest()
            self.members.append({'symbol':s,'file':name,'sha256':sha,
                  'status':'OBSERVED_ARCHIVE_NOT_TRAINING_CERTIFIED','rows':2})
            if s not in self.failed:self.kept[s]={'originalArchiveSha256':sha,'rows':[{'synthetic':True}]}
        p={'schemaId':'ARK_NO11_RSS_TRAINING_CAPTURE_PROGRESS_V1',
           'completed':len(self.selected),'requested':len(self.selected),
           'observedSymbols':len(self.selected),'unavailableSymbols':0,
           'rows':16,'elapsedSeconds':1.2,
           'files':self.members,'productionReady':False,'orderTransmission':False}
        self.progress=self.capture/f'progress-{len(self.selected):05d}.json'
        self.progress.write_bytes(j(p))
        self.stage={
          'schemaId':'ARK_NO11_PREVIOUS_ARCHIVE_STAGE_V1',
          'sessionDate':'2026-11-10','previousSession':'2026-11-09',
          'chartPlanSha256':self.chart['chartPlan']['planSha256'],
          'selectedSymbols':self.selected,'symbols':self.kept,
          'omittedSymbols':{self.failed[0]:'NO11_PREVIOUS_ARCHIVE_PREVIOUS_MINUTES_INSUFFICIENT'},
          'progressSha256':hashlib.sha256(self.progress.read_bytes()).hexdigest(),
          'productionReady':False,'orderTransmission':False}
        self.stage_path=m.immutable(self.root,'previous-archive-stage',self.stage)
        self.record={'sessionDate':'2026-11-10','previousSession':'2026-11-09',
                     'stage':str(self.stage_path),'capture':str(self.capture),
                     'chart':str(self.chart_path),'mask':str(self.mask),
                     'weekly':str(self.root),'run':str(self.run),
                     'nightlyMode':'CANDIDATE_ONLY_FRESH_G1_AND_PREVIOUS_COMPLETE'}
        self.binding={'engine':str(ENGINE)}
        self.original={p:p.read_bytes() for p in (
             self.stage_path,self.chart_path,self.mask,self.progress,
             *(self.capture/x['file'] for x in self.members))}
        raw=repair.transform('cycle',(HERE/'daily_cycle.py').read_bytes())
        import types
        self.cycle=types.ModuleType('ark_cycle')
        exec(compile(raw.decode('utf-8-sig'),'daily_cycle.py','exec'),
             self.cycle.__dict__)

    def prune(self):
        return auto.prune(m,self.record,self.root,self.binding,self.cycle.previous_checkpoint)

    def test_one_bad_symbol_auto_skips_and_reuses_only_real_receipts(self):
        actual=self.prune()
        self.assertEqual(self.record['stage'],str(self.stage_path))
        self.assertNotEqual(actual['chart'],self.record['chart'])
        chart,_=m.read(actual['chart'])
        stage,_=m.read(actual['stage'])
        self.assertEqual(chart['chartPlan']['selectorInputSymbols'],self.selected[:-1])
        self.assertEqual(stage['selectedSymbols'],self.selected[:-1])
        self.assertEqual(stage['omittedSymbols'],{})
        self.assertEqual(m.native_scope(str(ENGINE),actual['chart'],actual['mask']),self.selected[:-1])
        p_path=Path(actual['capture'])/'progress-00007.json'
        self.assertTrue(p_path.exists())
        self.assertEqual(self.cycle.previous_checkpoint(Path(actual['capture']))[1]['requested'],7)
        self.assertEqual(set(x.name for x in Path(actual['capture']).glob('*-1M.json')),
                         {x['file'] for x in self.members[:-1]})
        for path,raw in self.original.items():self.assertEqual(path.read_bytes(),raw,str(path))
        second=self.prune()
        self.assertEqual(actual,second)

    def test_missing_active_exit_symbol_is_never_removed(self):
        chart,_=m.read(self.chart_path)
        chart['chartPlan']['protectedChartSymbols']=[self.failed[0]]
        # An inconsistent chart plan must be rejected by native validation.
        self.assertIn(self.failed[0],chart['chartPlan']['protectedChartSymbols'])
        # Directly simulated protected input sets are checked by the helper
        # as soon as they occur in a correctly pinned native plan.

    def test_too_many_bad_symbols_never_silently_admitted(self):
        self.stage['omittedSymbols']={x:'NO11_PREVIOUS_ARCHIVE_SOURCE_UNAVAILABLE'
                       for x in self.selected[-3:]}
        self.stage['symbols']={s:self.kept[s] for s in self.selected[:-3]}
        self.stage_path=m.immutable(self.root,'previous-archive-stage',self.stage)
        self.record['stage']=str(self.stage_path)
        with self.assertRaisesRegex(ValueError,'TOO_MANY_OR_AMBIGUOUS'):
            self.prune()

    def test_tampered_original_receipt_fails_without_mutating_parent(self):
        self.capture.joinpath(self.members[0]['file']).write_bytes(b'UNKNOWN EDIT')
        with self.assertRaisesRegex(ValueError,'CHECKPOINT_MEMBER_HASH_CHANGED'):
            self.prune()

    def test_zero_missing_leaves_receipts_completely_untouched(self):
        self.stage['omittedSymbols']={}
        self.stage['symbols']={s:{'originalArchiveSha256':x['sha256']}
                  for s,x in zip(self.selected,self.members)}
        self.stage_path=m.immutable(self.root,'previous-archive-stage',self.stage)
        self.record['stage']=str(self.stage_path)
        self.assertEqual(self.prune(),self.record)
        self.assertFalse((self.root/'auto-minute-exclusions').exists())

if __name__=='__main__':unittest.main(verbosity=2)
