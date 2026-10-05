"""Aggregate already-saved concurrent frames over actual funded holding intervals."""
from pathlib import Path
from collections import defaultdict
from decimal import Decimal
from datetime import datetime
from zoneinfo import ZoneInfo
import csv,gzip,hashlib,json
REPO=Path(__file__).resolve().parents[2];ROOT=REPO.parent
OUT=REPO/'docs/evidence/capital-full-r-spectrum-20261006-v1';PRIVATE=ROOT/'capital_r_spectrum_private'
def rows(p):return [json.loads(s) for s in gzip.open(p,'rt') if s.strip()]
def main():
    binding=json.loads((OUT/'START_AND_SOURCE_BINDING.json').read_text());source=Path(binding['source_refs']['inputs']['native_curve']['local_path'])
    assert hashlib.sha256(source.read_bytes()).hexdigest()==binding['source_refs']['inputs']['native_curve']['sha256']
    frames={(r['session'],r['minute']):r['concurrent'] for r in rows(source)}
    joined=[r for r in rows(PRIVATE/'evaluation-only/ENTRY_JOINED_ANATOMY.jsonl.gz') if r['actual_funded_trade'] is not None]
    meta=json.loads((PRIVATE/'DERIVATION_COMPLETE.json').read_text());checks=0
    def summarize(rr):
        minutes=0;concurrent=0;capital_minutes=Decimal(0);capital_concurrent=Decimal(0);hist=defaultdict(int)
        for r in rr:
            t=r['actual_funded_trade'];debit=Decimal(t['debit'])
            for m in range(t['entry_minute'],t['release_minute']):
                n=frames[(t['session'],m)];assert 1<=n<=3
                minutes+=1;concurrent+=n;capital_minutes+=debit;capital_concurrent+=debit*n;hist[str(n)]+=1
        return {'trade_N':len(rr),'holding_minutes':minutes,'position_minutes_at_concurrent':dict(hist),
                'holding_concurrent_mean':concurrent/minutes if minutes else None,
                'capital_minutes_jpy':str(capital_minutes),
                'capital_weighted_concurrent_mean':str(capital_concurrent/capital_minutes) if capital_minutes else None}
    output={'schema':'ARK_SAVED_V5_HOLDING_OCCUPANCY_V1','exact_jst':datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),
       'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'method':'Lookup saved post-batch concurrent frame over actual [entry,release) minute interval; no policy/state replay',
       'position_minutes_note':'Per-trade holding observations overlap and count position-minutes, not distinct portfolio minutes','total':summarize(joined),
       'buckets':[{'bucket_pp_lower':k,**summarize([r for r in joined if r['bucket_pp_lower']==k])} for k in range(meta['bucket_lower_min'],meta['bucket_lower_max']+1)],
       'cumulative':[{'label':label,**summarize([r for r in joined if r['events'][label]])} for label in meta['labels']],
       'new_Capital_replays':0}
    (OUT/'V5_R_OCCUPANCY.json').write_text(json.dumps(output,indent=2,sort_keys=True)+'\n')
    with (OUT/'V5_R_OCCUPANCY.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(output['buckets'][0]));writer.writeheader()
        for r in output['buckets']:writer.writerow({k:json.dumps(v) if isinstance(v,dict) else v for k,v in r.items()})
    print(json.dumps({'actual_trade_N':len(joined),'total':output['total']}))
if __name__=='__main__':main()
