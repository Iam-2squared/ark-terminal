"""Independent first-passage arithmetic from frozen originals. Imports no main helper."""
import argparse
import collections
from decimal import Decimal
import gzip
import hashlib
import json
import datetime
from pathlib import Path

HERE=Path(__file__).resolve().parent
SUB=HERE.parents[1]/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate'
def read(p):
    b=Path(p).read_bytes();return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clock(day,left,right):
    a=max(0,min(right,690)-max(left,540));b=max(0,min(right,900 if day<'2024-11-05' else 925)-max(left,750));return a+b
def status(day,fill,price,bars,end_status):
    up=Decimal(str(price))*Decimal('1.02');down=Decimal(str(price))*Decimal('.99')
    terminal=900 if day<'2024-11-05' else 930;pm=900 if day<'2024-11-05' else 925
    schedule=list(range(540,691))+list(range(750,pm))+[terminal]
    for minute in schedule:
        if minute<fill:continue
        if minute not in bars:return 'DATA_UNAVAILABLE',None
        b=bars[minute];o,h,l,c=(Decimal(str(v)) for v in b[1:5])
        if min(o,h,l,c)<=0 or l>min(o,c) or h<max(o,c):return 'DATA_UNAVAILABLE',None
        if o>=up:return 'UP_FIRST',minute
        if o<=down:return 'DOWN_FIRST',minute
        if h>=up and l<=down:return 'ORDER_UNKNOWN',minute
        if h>=up:return 'UP_FIRST',minute
        if l<=down:return 'DOWN_FIRST',minute
    return ('NEITHER' if end_status=='AVAILABLE' else 'DATA_UNAVAILABLE'),None

def run(grid):
    rows=read(grid);outcomes=read(SUB/'outcomes.json.gz');raw=read(SUB/'raw-paths-evaluator-only.json.gz')
    population=read(SUB/'opportunities.json.gz')
    anchors={}
    for o in population:
        t=datetime.datetime.fromisoformat(o['origin']['decisionTimestamp'])
        anchors[o['id']]=t.hour*60+t.minute
    by=collections.defaultdict(list)
    for r in rows:by[r['opportunity']].append(r)
    expected={};caches={};counts=collections.Counter();fill_checks=first_checks=secondary_checks=0
    for oid,rr in by.items():
        rr.sort(key=lambda r:r['minute']);candidates=[r for r in rr if r['quoteAvailable'] and (outcomes.get(r['id']) or {}).get('price') is not None]
        bar_map={int(b[0]):b for b in raw[oid]['today']};cache={}
        for r in rr:
            fr=next((v for v in candidates if v['minute']>=r['minute']),None)
            if fr is None:expected[r['id']]=(None,None,None,'DATA_UNAVAILABLE',None);continue
            if fr['id'] not in cache:
                saved=outcomes[fr['id']];p0=saved['price'];start=fr['minute']
                assert start in bar_map and abs(bar_map[start][1]*1.0005-p0)<=max(1e-10,abs(p0)*1e-12)
                st,touch=status(r['session'],start,p0,bar_map,(saved.get('labels') or {}).get('fullStatus'))
                cache[fr['id']]=(fr['id'],start,p0,st,touch);fill_checks+=1
            expected[r['id']]=cache[fr['id']]
        caches[oid]=cache
    differences=[];delay_mismatch=0;row_n=0
    for line in gzip.open(HERE/'FIRST_PASSAGE_LABELS.jsonl.gz','rt'):
        x=json.loads(line);row_n+=1;ex=expected[x['row_id']];counts[x['primary_status']]+=1
        if x['fill_id']!=ex[0] or x['fill_minute']!=ex[1] or x['fill_price']!=ex[2] or x['primary_status']!=ex[3]:
            differences.append(dict(row_id=x['row_id'],main_status=x['primary_status'],independent_status=ex[3],fill_identity_match=x['fill_id']==ex[0]))
        if ex[0] is not None:
            g=x['grid']['+2/-1'];first_checks+=1
            if g.get('first_touch_bar_start')!=ex[4]:differences.append(dict(row_id=x['row_id'],field='first_touch_bar_start',main=g.get('first_touch_bar_start'),independent=ex[4]))
            # Order_UNKNOWN must be an actual two-touch bar with open inside both barriers.
            if x['primary_status']=='ORDER_UNKNOWN':
                bar=next(b for b in raw[x['opportunity']]['today'] if int(b[0])==ex[4]);p=Decimal(str(ex[2]));o,h,l=(Decimal(str(v)) for v in bar[1:4])
                assert p*Decimal('.99')<o<p*Decimal('1.02') and h>=p*Decimal('1.02') and l<=p*Decimal('.99')
            for down in (.5,1,2):
                sts=[x['grid'][f'+{up}/-{down:g}']['status'] for up in range(1,6)]
                for j in range(1,5):
                    assert sts[j]!='UP_FIRST' or sts[j-1]=='UP_FIRST',('UP_LEVEL_MIXUP',x['row_id'],down,j)
                    secondary_checks+=1
        r=rows[row_n-1]
        assert r['id']==x['row_id']
        first=anchors[r['opportunity']];delay=clock(r['session'],first,r['minute'])
        if delay!=r['delay'] or delay!=x['active_delay']:delay_mismatch+=1
    assert row_n==len(rows)==149900
    result=dict(status='INDEPENDENT_LABEL_ARITHMETIC_PASS' if not differences and not delay_mismatch else 'INDEPENDENT_LABEL_ARITHMETIC_FAIL',
        rows=row_n,opportunities=len(by),unique_fill_anchor_checks=fill_checks,first_touch_row_checks=first_checks,
        secondary_level_monotonicity_checks=secondary_checks,primary_counts=dict(counts),mismatch_count=len(differences),mismatch_examples=differences[:30],
        active_delay_mismatches=delay_mismatch,Decimal_route=True,main_label_helper_imported=False,
        source_grid_sha256=digest(grid),source_raw_sha256=digest(SUB/'raw-paths-evaluator-only.json.gz'),labels_sha256=digest(HERE/'FIRST_PASSAGE_LABELS.jsonl.gz'),
        Selector_anchor_source_sha256=digest(SUB/'opportunities.json.gz'),Selector_anchor='exact saved origin.decisionTimestamp; not first eligible candidate row',
        nonzero_first_grid_delay_opportunities=sum(v[0]['delay']!=0 for v in by.values()),
        new_model_fits=0,threshold_tuning=0,bootstrap_draws=0,provider_requests=0,new_label_creation_passes=0,
        scope='All149900 rows fill lineage/primary status/first touch and active delay; Decimal barrier arithmetic from original saved OHLC; secondary level monotonicity, not a second production label pass')
    (HERE/'C4_INDEPENDENT_LABEL_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result));assert result['status']=='INDEPENDENT_LABEL_ARITHMETIC_PASS'

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--grid',required=True);run(ap.parse_args().grid)
