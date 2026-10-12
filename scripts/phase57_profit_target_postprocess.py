"""Recover only descriptive postprocessing from the saved first-batch rows.

The main policy evaluator is never invoked here. Existing result bytes are
compared and retained; the failed original invocation remains INVALID_RUN.
"""
import gzip
import json
import shutil
import tempfile
from pathlib import Path

from scripts import phase57_profit_target_diagnostic as d
from scripts.phase57_profit_target_precommit import OUT, ARM, SOURCE, digest, jst, check


def run():
    bad=json.loads((OUT/'RUN_INVALID.json').read_text())
    check(bad['status']=='INVALID_RUN_POSTPROCESS_EXCEPTION' and
          digest(OUT/'FIXED_TARGET_OUTCOME_ROWS.jsonl.gz')==bad['savedRowsSha256'],
          'INVALID_RUN_IDENTITY')
    check(not (OUT/'POSTPROCESS_RECOVERY.json').exists(),'POSTPROCESS_REPEATED')
    rows=d.read_gz(OUT/'FIXED_TARGET_OUTCOME_ROWS.jsonl.gz')
    check(len(rows)==(819+795)*7 and
          len({(r['arm'],r['targetPct']) for r in rows})==14,'SAVED_POLICY_ROW_SCOPE')
    row_by_id={(r['arm'],r['entryId']):r for r in rows if r['targetPct']==3}
    _,entries,ledgers,controls,raw,skipped=d.load_verified()
    market=[]
    for a in ARM:
        funded=ledgers[a]['funded']
        for eid in sorted(entries[a]):
            e=entries[a][eid]
            filtered,invalid=d.valid_bars(raw[e['opportunityId']],e['session'],e['entryMinute'])
            saved=row_by_id[a,eid]
            market.append((a,e,controls[a][eid],filtered,invalid,funded.get(eid),
                           saved['sameTimestampRiskset'],
                           saved['initialOrReplacement']=='REPLACEMENT'))
    prior=d.OUT
    try:
        with tempfile.TemporaryDirectory() as folder:
            d.OUT=Path(folder)
            for name in ('BOOTSTRAP_SPEC.json','SESSION_DRAWS.npz',
                         'TARGET_FEATURE_REGISTRY.json','MEASUREMENT_PRECOMMIT.json'):
                shutil.copy2(prior/name,d.OUT/name)
            d.analyze(rows,market,ledgers,raw,skipped,
                      json.loads((prior/'MEASUREMENT_PRECOMMIT.json').read_text()))
            compared=[];added=[]
            for p in sorted(d.OUT.iterdir()):
                if p.name in ('BOOTSTRAP_SPEC.json','SESSION_DRAWS.npz',
                              'TARGET_FEATURE_REGISTRY.json','MEASUREMENT_PRECOMMIT.json'):
                    continue
                target=prior/p.name
                if target.exists():
                    check(digest(target)==digest(p),'POSTPROCESS_EXISTING_DRIFT:'+p.name)
                    compared.append(p.name)
                else:
                    shutil.copy2(p,target)
                    added.append(p.name)
    finally:
        d.OUT=prior
    rec={'status':'POSTPROCESS_RECOVERED_FROM_SAVED_ROWS_ONLY',
         'atJst':jst(),'originalInvocation':'INVALID_RUN_POSTPROCESS_EXCEPTION',
         'mainPolicyArmReevaluations':0,'sourceSavedRowsSha256':bad['savedRowsSha256'],
         'unchangedOutputHashesCompared':compared,'descriptiveOutputsAdded':added,
         'mainRunInvalidFlagRetained':True}
    (OUT/'POSTPROCESS_RECOVERY.json').write_bytes(d.canonical(rec))
    print(json.dumps(rec,ensure_ascii=False))


if __name__=='__main__':
    run()
