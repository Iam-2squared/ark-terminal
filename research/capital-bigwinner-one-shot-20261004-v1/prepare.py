"""Build causal X/liquidity; separately materialize evaluation teachers/source book."""
from collections import Counter
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
from checkpoint import ROOT, OUT, save, sha
from features import project,NUMERIC,CATEGORICAL
from contracts import liquidity,valid_market

SCRATCH=ROOT.parent
PRIVATE=SCRATCH/'bigwinner_private'

def rows(path):
    return [json.loads(s) for s in gzip.open(path,'rt')]

def gzwrite(path,values):
    data=gzip.compress(('\n'.join(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False) for r in values)+'\n').encode(),mtime=0)
    with Path(path).open('xb') as f:f.write(data)

def main():
    source_path=SCRATCH/'work_inputs/bigwinner_source/SAVED_SOURCE_PRIVATE.json.gz'
    receipt=json.loads((source_path.parent/'SAVED_SOURCE_RECEIPT.json').read_text())
    assert sha(source_path)==receipt['private_sha256']
    source_rows=json.load(gzip.open(source_path,'rt'))
    source={(r['session'],r['symbol']):r for r in source_rows}
    assert len(source)==len(source_rows)
    entries=[r for r in rows(SCRATCH/'work_inputs/exit_v2/FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz') if r['entry_status']=='FIRST_ENTRY']
    exits={r['watch_key']:r for r in rows(SCRATCH/'work_inputs/exit_v3/REPLAY_ROWS.jsonl.gz')}
    raw=json.load(gzip.open(SCRATCH/'work_inputs/exit_v2/SAVED_INPUTS/raw_paths_selected.json.gz','rt'))
    scope=json.loads((Path(__file__).parent/'SOURCE_RECOVERY_SCOPE.json').read_text())
    calendar=sorted(set(scope['required_prior_dates']+scope['entry_cohort_dates']))
    runtime=[];teachers=[];details=[];markets=[]
    counts=Counter();missing=Counter();mismatch=0
    for e in sorted(entries,key=lambda r:(r['session'],r['fill_minute'],r['symbol'])):
        key=e['watch_key'];day=e['session'];symbol=e['symbol'];t=e['fill_minute']
        path=SCRATCH/('work_inputs/exit_v2/FULL_TRACE/'+day+'_'+symbol+'.jsonl.gz')
        trace=rows(path)
        feature=project(e,trace)
        original=[r for r in raw[key]['today'] if int(r[0])==t]
        assert len(original)==1
        raw_price=Decimal(str(original[0][1]))
        assert abs(raw_price*Decimal('1.0005')-Decimal(str(e['fill_price'])))<Decimal('1e-8')
        liq=liquidity(day,symbol,raw_price,calendar,source)
        counts[liq['reason']]+=1
        for k,v in feature['numeric'].items():missing[k]+=v is None
        runtime.append({'entry_id':key,'session':day,'symbol':symbol,'entry_minute':t,
            'entry_timestamp':e['fill_timestamp'],'raw_reference':str(raw_price),
            'numeric':feature['numeric'],'categorical':feature['categorical'],
            'provenance':feature['provenance'],'liquidity':liq})
        same=source.get((day,symbol))
        complete=bool(same and same.get('minute_source',{}).get('date_scope_complete')
                      and same.get('minute_source',{}).get('terminal_pagination_proven'))
        market=same.get('market',[]) if same else []
        byminute={r['minute']:r for r in market}
        assert len(byminute)==len(market)
        # Equality to original Frozen raw sources, never silently replace Entry/EXIT.
        for o in raw[key]['today']:
            s=byminute.get(int(o[0]))
            if s:
                mismatch+=any(abs(Decimal(str(o[j]))-Decimal(str(s[k])))>Decimal('1e-7') for j,k in enumerate(('O','H','L','C','Vo','Va'),1))
        future=[r for r in market if t<r['minute']<920 and valid_market(r)]
        maximum=max((Decimal(str(r['H'])) for r in future),default=raw_price)
        potential=float(maximum/raw_price-1) if future else 0.0 if complete else None
        y=int(maximum/raw_price-1>=Decimal('.05')) if future and maximum/raw_price-1>=Decimal('.05') else 0 if complete else None
        teachers.append({'entry_id':key,'session':day,'label_bigwinner5':y,
            'potential_return':potential,'label_bigwinner3':int(potential>=.03) if potential is not None else None,
            'label_bigwinner10':int(potential>=.10) if potential is not None else None,
            'capture_complete':complete,'strictly_after_entry_before_1520':True,
            'scope':'Evaluation/teacher only; no Frozen EXIT PnL fields'})
        details.append({'entry_id':key,'liquidity':liq,'entry_state_prefix':feature['provenance']})
        markets.append({'entry_id':key,'session':day,'symbol':symbol,'capture_complete':complete,
            'source':same.get('minute_source') if same else None,'market':market,
            'entry_actual_source':byminute.get(t),'frozen_exit':exits[key],'limit_up_authority':None})
    assert mismatch==0,'FROZEN_RAW_VS_ORIGINAL_CACHE_CONFLICT'
    assert len(runtime)==1600 and len({r['session'] for r in runtime})==58
    gzwrite(PRIVATE/'RUNTIME_CAUSAL.jsonl.gz',runtime)
    gzwrite(PRIVATE/'TEACHERS_EVALUATION.jsonl.gz',teachers)
    gzwrite(PRIVATE/'MARKET_EXECUTION_BOOK.jsonl.gz',markets)
    report={'candidate_N':1600,'sessions_N':58,'runtime_numeric_fields':len(NUMERIC),'runtime_categorical_fields':len(CATEGORICAL),
        'numeric_missing_N':dict(missing),'liquidity_status':dict(counts),
        'source_complete_candidate_N':sum(r['capture_complete'] for r in teachers),
        'teacher_unknown_N':sum(r['label_bigwinner5'] is None for r in teachers),
        'labels_separate_from_runtime':True,'Frozen_raw_cache_conflicts':mismatch,
        'limit_up_authority_available_N':0,'runtime_sha256':sha(PRIVATE/'RUNTIME_CAUSAL.jsonl.gz'),
        'teacher_sha256':sha(PRIVATE/'TEACHERS_EVALUATION.jsonl.gz'),'source_book_sha256':sha(PRIVATE/'MARKET_EXECUTION_BOOK.jsonl.gz'),
        'protected_opened':0,'fits':0,'source_recovery_hash':sha(source_path),'source_receipt_hash':sha(source_path.parent/'SAVED_SOURCE_RECEIPT.json')}
    save(OUT/'FEATURE_LIQUIDITY_SOURCE_RESULT.json',report)
    # Append a new manifest; the initial source manifest is preserved.
    save(PRIVATE/'SOURCE_MANIFEST_RECOVERED.json',{'initial':json.loads((PRIVATE/'SOURCE_MANIFEST.json').read_text()),
        'saved_source_sha256':sha(source_path),'source_receipt_sha256':sha(source_path.parent/'SAVED_SOURCE_RECEIPT.json')})
    print(json.dumps(report))

if __name__=='__main__':main()
