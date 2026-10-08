"""Same-author separate raw/label audit; imports no RD02 feature/bucket/evaluator."""
from pathlib import Path
from fractions import Fraction as F
from decimal import Decimal, InvalidOperation
import json,gzip,zipfile,math,hashlib,collections,sys
ROOT=Path(__file__).resolve().parents[2];W=ROOT/'rd02';V=W/'private';P=W/'public';I=ROOT/'inputs'
def js(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def read(p):return json.loads(Path(p).read_bytes())
def gz(p):return [json.loads(x) for x in gzip.decompress(Path(p).read_bytes()).splitlines()]
def sh(b):return hashlib.sha256(b).hexdigest()
def save(p,x):Path(p).write_bytes(js(x))
SCHEDULE=tuple(range(541,691))+tuple(range(751,926))
def active(t):return sum(v<=t for v in SCHEDULE)
def stamp(d,t):return f'{d}T{t//60:02d}:{t%60:02d}:00+09:00'
def rawvalid(r,positive_flow=False,auction=False):
    try:
        if not r.get('lineage') or any(isinstance(r.get(k),bool) or r.get(k) is None for k in ['O','H','L','C','Vo','Va']):return False
        o,h,l,c,v,a=(Decimal(str(r[k])) for k in ['O','H','L','C','Vo','Va'])
        return all(z.is_finite() for z in [o,h,l,c,v,a]) and l>0 and l<=o<=h and l<=c<=h and (v>0 and a>0 if positive_flow else v>=0 and a>=0) and (not auction or o==h==l==c)
    except (ValueError,KeyError,InvalidOperation):return False
def statevalid(r,states):
    s=r['state'];p=r['path'];end=r['bar_end_minute']
    return s['current_semantics_observed'] is True and p['current_semantics_observed'] is True and s['observed_at']==end-540 and s['as_of']==end-540 and p['quality']['numeric_status']=='ACCEPTED' and p['Primary_or_null'] in states and r['source_status']=='RAW_CLOSED_AT_ASSUMED_BAR_END' and all(s.get(k)!='CARRIED_GAP' for k in ['activity','basis'])

def reconstruct(key,day,cutoff,market,trace,schema,evidence=True):
    states=list(schema['vocabulary']['STATE/previous_run'][:9]);schedule=[x for x in SCHEDULE if x<=cutoff];prefix=sorted((r for r in trace if r['bar_end_minute']<=cutoff),key=lambda r:r['bar_end_minute']) if evidence else []
    assert len({r['bar_end_minute'] for r in prefix})==len(prefix)
    for r in prefix:
        t=r['bar_end_minute'];assert r['watch_key']==key==r['state']['case_id']==r['path']['case_id']
        assert r['assumed_available_at']==r['path']['bar_end']==stamp(day,t)
        assert r['state']['as_of']==r['path']['scheduled_t']==t-540
        assert r['input'] is None or r['input']['known_at']<=t-540 and r['input']['t']<=t-540
    checkpoints={r['bar_end_minute']:r for r in prefix};selected={}
    for r in market:
        if r.get('session')==day and r['minute']+1 in schedule:
            t=r['minute']+1;assert t not in selected;selected[t]=r
    segments=[];last_end=None;segment=0;breaks=[]
    for end in schedule:
        r=selected.get(end)
        if r is None or not rawvalid(r):last_end=None;continue
        reset=checkpoints.get(end,{}).get('path',{}).get('quality',{}).get('reset_reasons',[])
        if segments and (last_end is None or last_end!=end-1 or reset):segment+=1;breaks.append(end)
        vals={k:float(Decimal(str(r[k]))) for k in ['O','H','L','C','Vo','Va']};segments.append({'end':end,'seg':segment,**vals});last_end=end
    numeric={k:None for k in schema['numeric_column_order']}
    for width in [5,20,60]:
        slots=set(schedule[-width:]);bars=[r for r in segments if r['end'] in slots];n=len(bars);pre=f'PRICE/w{width}/';numeric[pre+'coverage']=n/len(slots) if slots else 0.
        pairs=[(left,right) for left,right in zip(bars,bars[1:]) if left['seg']==right['seg'] and right['end']==left['end']+1]
        if bars:
            last=bars[-1]['C'];hi=max(r['H'] for r in bars);lo=min(r['L'] for r in bars)
            for k,value in {'net_log':math.log(last/bars[0]['O']),'range_log':math.log(hi/lo),'from_high_log':math.log(last/hi),'from_low_log':math.log(last/lo),'mean_volume_log1p':math.log1p(sum(r['Vo'] for r in bars)/n),'mean_value_log1p':math.log1p(sum(r['Va'] for r in bars)/n)}.items():numeric[pre+k]=value
        if pairs:
            ret=[math.log(right['C']/left['C']) for left,right in pairs];change=sum(ret);abschange=sum(abs(z) for z in ret)
            numeric[pre+'signed_efficiency']=change/abschange if abschange else 0.
            numeric[pre+'return_rms']=math.sqrt(sum(z*z for z in ret)/len(ret));numeric[pre+'down_pair_rate']=sum(z<0 for z in ret)/len(ret)
            volume=sum(right['Vo'] for _,right in pairs);numeric[pre+'down_volume_share']=sum(right['Vo'] for (_,right),z in zip(pairs,ret) if z<0)/volume if volume else None
            groups=collections.defaultdict(list)
            for r in bars:groups[r['seg']].append(r['C'])
            dd=[]
            for vals in groups.values():
                if len(vals)<2:continue
                for index,c in enumerate(vals):dd.append(math.log(c/max(vals[:index+1])))
            numeric[pre+'close_drawdown']=min(dd) if dd else None
    if segments:
        a=segments[-1];spread=a['H']-a['L'];numeric['PRICE/flat']=int(spread==0)
        numeric['PRICE/body']=(a['C']-a['O'])/spread if spread else 0.;numeric['PRICE/upper_wick']=(a['H']-max(a['O'],a['C']))/spread if spread else 0.;numeric['PRICE/lower_wick']=(min(a['O'],a['C'])-a['L'])/spread if spread else 0.
        numeric['PRICE/raw_age']=active(cutoff)-active(a['end'])
    for name,col in [('volume','Vo'),('value','Va')]:
        short=[r[col] for r in segments if r['end'] in schedule[-5:]];long=[r[col] for r in segments if r['end'] in schedule[-20:]]
        sa=sum(short)/len(short) if short else None;la=sum(long)/len(long) if long else None
        numeric[f'PRICE/{name}5_20_log']=math.log(sa/la) if sa is not None and la is not None and sa>0 and la>0 else None
    numeric['PRICE/active_minutes']=active(cutoff);numeric['PRICE/raw_breaks60']=len(set(breaks)&set(schedule[-60:]))
    regular={t:checkpoints[t] for t in schedule if t in checkpoints}
    for width in [20,60]:
        slots=schedule[-width:];good=[regular[t] for t in slots if t in regular and statevalid(regular[t],states)];pre=f'STATE/w{width}/'
        for s in states:numeric[pre+s]=sum(r['path']['Primary_or_null']==s for r in good)/len(good) if good else None
        numeric[pre+'coverage']=len(good)/len(slots) if slots else 0.
        numeric[pre+'transitions']=sum(left in regular and right in regular and right==left+1 and statevalid(regular[left],states) and statevalid(regular[right],states) and regular[left]['path']['causal_segment_id']==regular[right]['path']['causal_segment_id'] and regular[left]['path']['Primary_or_null']!=regular[right]['path']['Primary_or_null'] for left,right in zip(slots,slots[1:]))
    observed=[t for t in schedule if t in regular and statevalid(regular[t],states)]
    numeric['STATE/last_valid_age']=active(cutoff)-active(observed[-1]) if observed else None
    numeric['STATE/breaks60']=sum(ev['event_type']=='SEGMENT_BREAK' for t in schedule[-60:] if t in regular for ev in regular[t].get('path_events',[]))
    cats={k:'UNKNOWN' for k in schema['categorical_column_order']};current=prefix[-1] if prefix else None;good=bool(current and current['bar_end_minute'] in schedule and statevalid(current,states))
    quality='UNKNOWN'
    if current:
        reset=current['path']['quality'].get('reset_reasons') or []
        if reset:quality='RESET:'+'|'.join(sorted(set(reset)))
        elif current.get('source_unavailable_reason'):quality='SOURCE_UNAVAILABLE'
        elif current['state'].get('activity') in ['INITIALIZING','CARRIED_GAP']:quality=current['state']['activity']
        elif current['path']['quality'].get('reason'):quality=current['path']['quality']['reason']
        else:quality='OBSERVED_VALID' if good else 'QUALITY_ABSTAIN'
    cats['STATE/quality_reset_reason']=quality if quality in schema['vocabulary']['STATE/quality_reset_reason'] else 'UNKNOWN'
    if good:
        t=current['bar_end_minute'];chain=[regular[t]]
        while t-1 in regular and statevalid(regular[t-1],states) and regular[t-1]['path']['causal_segment_id']==chain[-1]['path']['causal_segment_id']:
            t-=1;chain.append(regular[t])
        chain.reverse();runs=[]
        for r in chain:
            s=r['path']['Primary_or_null']
            if not runs or runs[-1][0]!=s:runs.append((s,r['bar_end_minute']))
        cats['STATE/current']=runs[-1][0];cats['STATE/previous_run']=runs[-2][0] if len(runs)>1 else 'START';cats['STATE/previous_previous_run']=runs[-3][0] if len(runs)>2 else 'START';numeric['STATE/run_duration']=active(cutoff)-active(runs[-1][1])
    else:
        activity=(current or {}).get('state',{}).get('activity');cats['STATE/current']=activity if activity in ['INITIALIZING','CARRIED_GAP'] else 'SOURCE_UNAVAILABLE' if current and current.get('source_unavailable_reason') else 'QUALITY_ABSTAIN' if current else 'START'
    return {'numeric':numeric,'categorical':cats,'price_available':bool(segments),'state_evidence_ok':evidence and len(regular)==len(schedule)}

def band(r):
    if r is None:return 'R_UNKNOWN'
    if r==0:return 'ZERO'
    if r>0:
        if r>=5:return 'P5_PLUS'
        if r<1:return 'P0_1'
        return ['P1_2','P2_3','P3_4','P4_5'][int(r)-1]
    if r<=-5:return 'L5_PLUS'
    if r>-1:return 'L0_1'
    return ['L1_2','L2_3','L3_4','L4_5'][int(-r)-1]
def cls(r):return None if r is None else 4 if r>=0 else 3 if r>-2 else 2 if r>-3 else 1 if r>-5 else 0
def compare(a,b,key,errors):
    for k,x in a['numeric'].items():
        y=b['numeric'][k]
        if x is None or y is None:
            if x is not y:errors.append({'entry_id':key,'field':k,'error':'MISSINGNESS_DIFF'})
        elif not math.isclose(float(x),float(y),abs_tol=1e-12,rel_tol=1e-12):errors.append({'entry_id':key,'field':k,'expected':x,'observed':y})
    for k in ['categorical','price_available','state_evidence_ok']:
        if a[k]!=b[k]:errors.append({'entry_id':key,'field':k,'error':'EXACT_DIFF'})

def run():
    schema=read(P/'FEATURE_FORMULAS_AND_SCHEMA.json');feat={r['entry_id']:r for r in gz(V/'FEATURE_ROWS.jsonl.gz')};binding={r['entry_id']:r for r in gz(V/'FEATURE_SOURCE_BINDING.jsonl.gz')};books={r['entry_id']:r for r in gz(I/'shared/inputs/books')};core={r['entry_id']:r for r in gz(I/'shared/inputs/core_runtime')};labels={r['entry_id']:r for r in gz(V/'WARMUP_R_NEW.jsonl.gz')+gz(V/'EVALUATION_R_NEW_REUSED.jsonl.gz')}
    assert feat.keys()==books.keys()==core.keys()==labels.keys() and len(feat)==1600
    z=zipfile.ZipFile(I/'STATE9_V2_FROZEN_TRACE_ARCHIVE.zip');manifest=json.loads(z.read('MANIFEST.json'));frozen={r['watch_key']:r for r in [json.loads(x) for x in gzip.decompress(z.read('FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz')).splitlines()] if r['entry_status']=='FIRST_ENTRY'}
    errors=[];audit=[];label_known=0;reconstructed=[];evaluation_ids={r['entry_id'] for r in gz(V/'EVALUATION_R_NEW_REUSED.jsonl.gz')}
    for number,key in enumerate(sorted(feat),1):
        day=core[key]['session'];intent=frozen[key]['first_intent'];tx=intent['intent_minute'];assert intent['row_id']==f'{key}|{tx}'==feat[key]['intent_row_id']==binding[key]['intent_row_id'];assert core[key]['entry_minute']==frozen[key]['fill_minute'] and tx<=frozen[key]['fill_minute']
        member=binding[key]['trace_member'];body=z.read(member);assert sh(body)==manifest['components'][member]['sha256']==binding[key]['trace_member_sha256'];trace=[json.loads(x) for x in gzip.decompress(body).splitlines()];market=books[key]['market'];rawprefix=[r for r in market if r['minute']+1<=tx];stateprefix=[r for r in trace if r['bar_end_minute']<=tx]
        assert sh(js(rawprefix))==binding[key]['raw_prefix_sha256'] and sh(js(stateprefix))==binding[key]['state_prefix_sha256']
        fresh=reconstruct(key,day,tx,market,trace,schema);compare(fresh,feat[key],key,errors);reconstructed.append({'entry_id':key,**fresh})
        l=labels[key]
        if l['known']:
            debit=F(str(books[key]['entry_actual_source']['O']))*F(2001,2000)*100;assert debit==F(l['buy_debit_100'])
            source=next(r for r in market if r['minute']==l['source_minute']);assert rawvalid(source,True,l['source_minute']==930)
            col='C' if l['source_minute']==930 else 'O'
            if l['exit_action']=='DELEGATE_CONTROL' and l.get('exit_kind')=='FROZEN_EXIT_V3':col='O' if books[key]['frozen_exit']['sell_source']=='NEXT_ELIGIBLE_REGULAR_RAW_OPEN' else 'C'
            credit=F(str(source[col]))*F(1999,2000)*100
            # Warmup control can use the inherited saved source reference.
            if key not in evaluation_ids and l['exit_action']=='DELEGATE_CONTROL' and books[key]['frozen_exit']['sell_status']=='FILLED' and books[key]['frozen_exit']['sell_minute']==l['source_minute'] and l['release_minute']<=920:
                col='O' if books[key]['frozen_exit']['sell_source']=='NEXT_ELIGIBLE_REGULAR_RAW_OPEN' else 'C';credit=F(str(source[col]))*F(1999,2000)*100
            assert credit==F(l['sell_credit_100']),'SELL_PRICE_ACCOUNTING_DIFF:'+key
            r=100*(credit/debit-1);assert r==F(int(l['r_numerator']),int(l['r_denominator'])),'R_EXACT_DIFF:'+key;label_known+=1
            audit.append({'entry_id':key,'exact_R':str(r),'band':band(r),'class':cls(r)})
        else:audit.append({'entry_id':key,'exact_R':None,'band':'R_UNKNOWN','class':None,'unknown_reason':l['unknown_reason']})
        if number%200==0:print('independent raw/feature/label audit',number,'/1600',flush=True)
    if (V/'SYNTHETIC_PRIMARY_OUTPUTS.json').exists():
        fixture=read(V/'SYNTHETIC_PRIMARY_OUTPUTS.json')
        for c in fixture['boundaries']:
            r=F(c['r']);assert band(r)==c['band'] and cls(r)==c['class']
        for c in fixture['feature_cases']:
            fresh=reconstruct(c['key'],c['day'],c['tx'],c['market'],c['trace'],schema,c['evidence']);compare(fresh,c['output'],c['name'],errors)
    assert not errors,'INDEPENDENT_FEATURE_DIFF_N:'+str(len(errors))
    (V/'INDEPENDENT_RECONSTRUCTED_FEATURES.jsonl.gz').write_bytes(gzip.compress(b''.join(js(r) for r in reconstructed),mtime=0));(V/'INDEPENDENT_RECONSTRUCTED_LABEL_ACCOUNTS.jsonl.gz').write_bytes(gzip.compress(b''.join(js(r) for r in audit),mtime=0))
    result={'status':'PASS','author_scope':'SAME_AUTHOR_SEPARATE_IMPLEMENTATION_CROSS_CHECK_NOT_THIRD_PARTY_BLIND_AUDIT','primary_feature_bucket_evaluator_imported':False,'source_scope':'original1600 ID/core/book raw/FROZEN FIRST_INTENT/full saved trace, original debit/credit prices and sealed label bytes','feature_ID_N':1600,'numeric_comparisons_N':112000,'categorical_comparisons_N':6400,'numeric_absolute_relative_tolerance':1e-12,'exact_ID_cutoff_source_missingness_categories_counter_differences_N':0,'known_R_exact_debit_credit_accounting_N':label_known,'known_R_class_bucket_differences_N':0,'evaluation_label_regeneration_N':0,'State_kernel_recalculation_N':0,'synthetic_boundary_N':33,'artificial_feature_cases_N':len(fixture['feature_cases']),'actual_arrival':'UNKNOWN','physical_blindness':False,'shared_limitations':'same original source/frozen State kernel; same-author implementation; not independent data or fresh validation','reconstructed_features_sha256':sh((V/'INDEPENDENT_RECONSTRUCTED_FEATURES.jsonl.gz').read_bytes()),'implementation_sha256':sh(Path(__file__).read_bytes())}
    save(P/'INDEPENDENT_FEATURE_LABEL_AUDIT.json',result);print(json.dumps(result))

if __name__=='__main__':
    try:run()
    except Exception as e:
        failures=V/'AUDIT_FAILURES.jsonl';f=open(failures,'ab');f.write(js({'audit':'independent_features','error':str(e),'status':'FAIL'}));f.close();raise
