"""Independent scalar inference, past-only tables and dominance. Primary imports=0."""
from independent_engine import *
import numpy as np
BUCKETS=[(540,570),(570,600),(600,630),(630,660),(660,690),(750,780),(780,810),(810,840),(840,870),(870,900),(900,920)]
def scalar(row,artifact):
    p=artifact['preprocessing'];nf=p['numeric_fields'];vals=[row['numeric'][k] for k in nf]
    numeric=[0. if v is None else float(v) for v in vals]+[float(v is None) for v in vals]
    feature=[(v-m)/s for v,m,s in zip(numeric,p['numeric_mean'],p['numeric_scale'])]
    for field in p['categorical_fields']:
        vocab=p['categorical_train_vocab'][field];v=row['categorical'][field];v=v if v in vocab else '__UNKNOWN__'
        feature.extend(float(v==c) for c in vocab)
    assert len(feature)==len(artifact['coef']) and all(math.isfinite(v) for v in feature)
    z=math.fsum(x*w for x,w in zip(feature,artifact['coef']))+artifact['intercept']
    return 1/(1+math.exp(-z)) if z>=0 else math.exp(z)/(1+math.exp(z))
def active(t):return t-540 if t<=690 else 150 if t<750 else t-600
def predicted(r,table):
    lo,hi=next((lo,hi) for lo,hi in BUCKETS if lo<=r['entry_minute']<hi)
    d=table['tenure']['cells'][r['band']][f'{lo}-{hi}']['median_active_duration'];a=active(r['entry_minute'])+d
    return min(920,a+540 if a<=150 else a+600),d
def accept(arm,r,occupancy,t,table):
    assert arm in ARMS and t==r['entry_minute'] and 0<=occupancy<=3
    if occupancy==3:return False,'MAX3_FULL',None,None
    horizon=predicted(r,table)[0];hits=0;n=len(table['training_sessions'])
    for day in table['training_sessions']:
        better=0
        for f in table['sessions'][day]:
            if f['entry_minute']<=t or f['entry_minute']>=horizon or f['r']<=r['r']:continue
            if f['q2']<r['q2']:continue
            if arm==ARMS[1] and f['q3']<r['q3']:continue
            better+=1
        if better>=3-occupancy:hits+=1
    ok=hits/n<0.5
    return ok,'ACCEPT_CAPACITY' if ok else 'CAPACITY_RESERVE_REJECT',hits,n
def native(units,n,counts):
    accum=0
    for j,old in enumerate('SAB'):
        accum+=counts[old]
        if units>n-accum:return BANDS[j]
    return BANDS[3]
def build(audit):
    raw=rows(Q/'inputs/RUNTIME_CAUSAL.jsonl.gz');rm={r['entry_id']:r for r in raw};core={r['entry_id']:r for r in rows(I/'core/CORE_RUNTIME_CAUSAL.jsonl.gz')}
    split=read(ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json');savedtrain=rows(PIN/'TRAIN_MAPPED_SCORES.jsonl.gz');savedruntime={r['entry_id']:r for r in rows(PIN/'RANK_NATIVE_RUNTIME.jsonl.gz')}
    stream=rows(I/'movement/MOVE_P5_SCORE_STREAM.jsonl.gz');savedpred={(r['head'],r['entry_id']):r['probability'] for r in rows(Q/'private/NEW_HEAD_OOF_PREDICTIONS.jsonl.gz')}
    # Historical tenure input is an explicit release-only projection. No quality labels.
    release={r['entry_id']:{k:r.get(k) for k in ('execution_status','release_minute')} for r in rows(I/'evaluation/TEACHERS_EVALUATION.jsonl.gz')}
    books={r['entry_id']:r for r in rows(I/'execution/MARKET_EXECUTION_BOOK_V2.jsonl.gz')};tables={};current=[];training=[]
    for block in split['blocks']:
        b=block['block'];pm=read(I/f'movement/models/MOVE_P_BLOCK_{b:02}.json');heads=[read(Q/f'private/models/MOVE_U{h}_BLOCK_{b:02}.json') for h in (2,3)];nn=len(pm['train_entry_ids'])
        rr=[dict(r) for r in savedtrain if r['block']==b];audit.check(f'{b}/ID',set(r['entry_id'] for r in rr)==set(pm['train_entry_ids']))
        oldheads=[read(I/f'current/models/H{h}_BLOCK_{b:02}.json') for h in (2,3,5)];base=sum(h['base_rate'] for h in oldheads)
        for h,model in zip((2,3),heads):
            audit.check(f'{b}/{h}/prep',model['preprocessing']==pm['preprocessing']);audit.check(f'{b}/{h}/ids',model['train_entry_ids']==pm['train_entry_ids'])
            state=np.load(Q/f'private/models/MOVE_U{h}_BLOCK_{b:02}_FITTED_STATE.npz',allow_pickle=False)
            audit.check(f'{b}/{h}/coef',np.array_equal(state['coef'][0],model['coef']));audit.check(f'{b}/{h}/intercept',state['intercept'][0]==model['intercept'])
        for r in rr:
            k=r['entry_id'];audit.num(f'{b}/{k}/pP_train',scalar(rm[k],pm),r['pP'])
            ml=sum(scalar(core[k],h) for h in oldheads)/base;audit.num(f'{b}/{k}/oldML',ml,r['old_ML'])
            for h,model in zip((2,3),heads):r[f'q{h}']=scalar(rm[k],model)
            audit.check(f'{b}/{k}/past',r['session'] in block['train'] and r['session']<min(block['test']))
        rr.sort(key=key);counts=Counter('S' if r['old_ML']>=2 else 'A' if r['old_ML']>=1.5 else 'B' if r['old_ML']>=1 else 'C' for r in rr);counts={k:counts[k] for k in 'SABC'}
        # Frozen pP ordering is the authority; inference differences never remap ranks.
        keys=[(-r['pP'],r['entry_timestamp'],r['symbol']) for r in rr]
        for j,r in enumerate(rr):
            audit.check(f'{b}/{r["entry_id"]}/rank',r['rank_units']==nn-j and r['r']==(nn-j)/nn and r['band']==native(nn-j,nn,counts))
        for s in [s for s in stream if s['block']==b]:
            k=s['entry_id'];units=nn-bisect_left(keys,(-s['pP'],s['entry_timestamp'],s['symbol']))
            r={f:s[f] for f in ('entry_id','session','symbol','entry_minute','entry_timestamp','raw_reference','pP','block')};r.update(rank_units=units,train_N=nn,r=units/nn,band=native(units,nn,counts))
            audit.check(k+'/rank_native_exact',all(r[f]==savedruntime[k][f] for f in r));audit.num(k+'/pP_scalar',scalar(rm[k],pm),s['pP'])
            for h,model in zip((2,3),heads):r[f'q{h}']=scalar(rm[k],model);audit.num(k+f'/q{h}_saved',r[f'q{h}'],savedpred[f'MOVE_U{h}',k])
            current.append(r)
        cells=defaultdict(list);band_values=defaultdict(list);global_values=[];support=[]
        for r in rr:
            if r['band']=='P_BELOW':continue
            z=release[r['entry_id']]
            if z['execution_status']!='COMPLETE' or z['release_minute'] is None:continue
            source=early(books[r['entry_id']]) or late(books[r['entry_id']]);audit.check(r['entry_id']+'/past_release',source is not None and source['release']==z['release_minute'])
            duration=max(1,sum(t<690 or t>=750 for t in range(r['entry_minute'],z['release_minute'])));lo,hi=next((lo,hi) for lo,hi in BUCKETS if lo<=r['entry_minute']<hi)
            cells[r['band'],f'{lo}-{hi}'].append(duration);band_values[r['band']].append(duration);global_values.append(duration);support.append(r['entry_id'])
        def med(x):return max(1,sorted(x)[(len(x)-1)//2])
        tenure={'cells':{},'training_support_N':len(global_values),'global_median_active_duration':med(global_values),'training_support_entry_ids':sorted(support),'teacher_projection_fields':['entry_id','execution_status','release_minute']}
        for band in BANDS[:3]:
            tenure['cells'][band]={}
            for lo,hi in BUCKETS:
                cell=f'{lo}-{hi}';x=cells[band,cell];backoff='CELL'
                if len(x)<10:x=band_values[band];backoff='BAND'
                if len(x)<10:x=global_values;backoff='GLOBAL'
                tenure['cells'][band][cell]={'cell_support_N':len(cells[band,cell]),'band_support_N':len(band_values[band]),'used_support_N':len(x),'backoff':backoff,'median_active_duration':med(x)}
        audit.check(f'{b}/tenure_exact',tenure==read(PARENT/'B2_TENURE_LOOKUP_TABLE.json')[str(b)])
        clean=[{k:r[k] for k in ('entry_id','session','entry_minute','r','q2','q3','band','block')} for r in rr];training+=clean
        tables[str(b)]={'training_sessions':block['train'],'test_sessions':block['test'],'tenure':tenure,'sessions':{day:[r for r in clean if r['session']==day and r['band']!='P_BELOW'] for day in block['train']}}
    current.sort(key=lambda r:(r['session'],r['entry_minute'],*key(r)));training.sort(key=lambda r:(r['block'],r['session'],r['entry_minute'],r['entry_id']))
    return current,tables,training
