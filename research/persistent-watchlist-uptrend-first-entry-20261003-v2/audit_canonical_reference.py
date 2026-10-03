"""Independent count supplement for quoted canonical baselines. Audit fit=0."""
import collections,datetime,gzip,json,pathlib
from zoneinfo import ZoneInfo
HERE=pathlib.Path(__file__).resolve().parent
def load(name):return json.loads((HERE/name).read_text())
def run():
    aggregate=load('ENTRY_HIGH_EVALUATION.json')
    checked={}
    for arm in ['IMMEDIATE','R1']:
        with gzip.open(HERE/f'BASELINE_{arm}_PAIRED_FIRST_WATCH.jsonl.gz','rt') as f:
            records=[json.loads(line) for line in f]
        keys=[r['watch_key'] for r in records]
        filled=sum(r['entry_status']=='FIRST_ENTRY' for r in records)
        reference=aggregate['canonical_2155_event_reference'][arm]
        assert len(keys)==len(set(keys))==reference['watch_N']==2155
        assert filled==reference['FIRST_ENTRY_N']==aggregate['primary_watch_summaries'][arm]['FIRST_ENTRY_N']
        checked[arm]={'watch_N':len(keys),'saved_filled_N':filled}
    receipt={'saved_at_jst':datetime.datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),'status':'PASS','checks':checked,'audit_fit':0,'metrics_changed':False,'entry_records_changed':False,'supplement_only':'canonical reference count metadata; main audit remains BLOCKED'}
    (HERE/'CANONICAL_REFERENCE_COUNT_AUDIT.json').write_text(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    audit=load('INDEPENDENT_AUDIT.json')
    audit['checks']['canonical reference population and saved filled count']=2
    audit['total_checks']=sum(audit['checks'].values())
    audit['canonical_reference_count_supplement']=receipt
    (HERE/'INDEPENDENT_AUDIT.json').write_text(json.dumps(audit,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':run()
