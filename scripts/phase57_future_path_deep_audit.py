"""STEP 1 only: immutable future-path audit; no research-module imports or fitting."""
from __future__ import annotations
import argparse, ast, collections, copy, csv, gzip, hashlib, html, io, json, math, subprocess
from pathlib import Path
from types import SimpleNamespace
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = '4ec55bb6923d0f69fbc9654ad33bb61cd2840780'
PROTOCOL_COMMIT = '5b7fdbedf93598bc8eed891010cdea5ab5d43009'
BASE = Path('docs/evidence/phase57-future-path-deep-audit-v1')
OLD = Path('docs/evidence/phase57-causal-entry-state-v1/ci-result/measurement')
SUB = Path('docs/evidence/phase57-entry-pattern-v2/ci-result/substrate')
CONTRACT = Path('docs/evidence/phase57-entry-timing-signal-census-v1/protocol.json')
PATHS = ('DIRECT_CONTINUATION','PULLBACK_RECOVERY','CONSOLIDATION_BREAKOUT','MULTI_SWING_CHOP','PERSISTENT_WEAKNESS','AMBIGUOUS_INSUFFICIENT')
EXPECTED = dict(zip(PATHS, (50,202,10,828,76,989)))
REASONS = {'INSUFFICIENT_OBSERVATION':496,'NO_DOMINANT_PATH':355,'TRUE_MIXED_PATH':138}
SAFETY = dict.fromkeys(('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted'), False)
CODE = ('phase57_causal_entry_anatomy.py','phase57_entry_timing_census.py','phase57_entry_timing_signals.py','phase57_causal_entry_state.py','phase57_entry_pattern_v2.py')
METRICS = ('rows','remainingActive','missingRegular','efficiency','reversals','directionChanges','terminalReturnPct','rangePct','orderedRangePct','volatilityPct','closeLocation','closingRecoveryPct','belowSelectorFraction','swingAmplitudeMedianPct','swingAmplitudeMaxPct','lowActiveDelay','highActiveDelay','orderedLowActiveDelay','orderedHighActiveDelay','contiguousSegments','longestSegment','upMovePct','downMovePct')


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
    p=Path(p); data=p.read_bytes()
    return json.loads(gzip.decompress(data) if p.suffix=='.gz' else data)
def clean(x):
    if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [clean(v) for v in x]
    if isinstance(x,np.generic): return clean(x.item())
    if isinstance(x,float) and not math.isfinite(x): raise ValueError('NONFINITE_OUTPUT')
    return x

def write(p,value):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    data=(json.dumps(clean(value),sort_keys=True,ensure_ascii=False,indent=None if p.suffix=='.gz' else 2,allow_nan=False)+'\n').encode()
    p.write_bytes(gzip.compress(data,mtime=0) if p.suffix=='.gz' else data)

def pin(path,ref=REFERENCE,root=ROOT):
    path=Path(path);data=(root/path).read_bytes()
    expected=subprocess.check_output(['git','rev-parse',f'{ref}:{path.as_posix()}'],cwd=root,text=True).strip()
    actual=hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()
    if actual!=expected: raise ValueError('SOURCE_CHANGED:'+str(path))
    return {'gitBlob':expected,'sha256':hashlib.sha256(data).hexdigest(),'referenceCommit':ref}

def extract(path,names,namespace):
    tree=ast.parse(Path(path).read_text())
    found={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
    nodes=[]
    for name in names:
        node=copy.deepcopy(found[name]);node.decorator_list=[];nodes.append(node)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),namespace)
    return SimpleNamespace(**{n:namespace[n] for n in names})

def frozen(root=ROOT):
    ns={'np':np,'PATHS':PATHS,'EMPTY':np.empty((0,7))}
    ns['s']=extract(root/'scripts'/CODE[2],('pct','regular'),ns)
    ns['e']=extract(root/'scripts'/CODE[4],('minutes',),ns)
    ns['c']=extract(root/'scripts'/CODE[1],('future_rows','ordered_oracle'),ns)
    ns['st']=extract(root/'scripts'/CODE[3],('efficiency',),ns)
    extract(root/'scripts'/CODE[0],('reversal_count','classify'),ns)
    return SimpleNamespace(**ns)

def distribution(values):
    values=list(values);x=np.asarray([v for v in values if v is not None],float)
    result={'n':len(x),'missing':len(values)-len(x)}
    for k,q in [('min',0),('p10',10),('p25',25),('median',50),('p75',75),('p90',90),('max',100)]:
        result[k]=float(np.percentile(x,q)) if len(x) else None
    result['mean']=float(np.mean(x)) if len(x) else None
    return result

def groups_of_minutes(ms):
    result=[]
    for t in sorted(set(ms)):
        if result and t==result[-1][-1]+1: result[-1].append(t)
        else: result.append([t])
    return [{'first':g[0],'last':g[-1],'n':len(g)} for g in result]

def observation(day,start,a,full,F):
    expected=[m for m in F.e.minutes(day) if m>=start]
    observed={int(x) for x in a[:,0]};missing=[m for m in expected if m not in observed]
    failures=[]
    if not full: failures.append('INHERITED_FULL_UNAVAILABLE')
    if len(a)<20: failures.append('ROWS_LT20')
    if len(expected)<30: failures.append('REMAINING_LT30')
    primary=('EMPTY_PATH' if not len(a) else 'REMAINING_LT30' if len(expected)<30 else
             'ROWS_LT20' if len(a)<20 else 'INHERITED_FULL_UNAVAILABLE' if not full else 'SUFFICIENT')
    end=900 if day<'2024-11-05' else 925;auction=900 if day<'2024-11-05' else 930
    return {'rows':len(a),'remainingActive':len(expected),'observedRegular':len(expected)-len(missing),
            'missingRegular':len(missing),'missingMinutes':missing,'missingRuns':groups_of_minutes(missing),
            'gateFailures':failures,'gateMask':'|'.join(failures) or 'NONE','primaryReason':primary,
            'fullSessionEvaluable':bool(full),'firstMinute':int(a[0,0]) if len(a) else None,
            'lastMinute':int(a[-1,0]) if len(a) else None,'terminalAuctionObserved':auction in observed,
            'nearMorningEnd':660<=start<=690,'nearAfternoonEnd':end-30<=start<=auction,
            'selectionHalf':'AM' if start<=690 else 'PM','crossesLunch':start<690 and any(m>=750 for m in observed),
            'morningRows':sum(t<=690 for t in observed),'afternoonRows':sum(t>=750 for t in observed),
            'sourceCause':'UNRESOLVED_SOURCE_CAUSE' if missing or not full else 'NO_COMPACT_COVERAGE_DEFECT_OBSERVED'}

def reversals_with_witness(a,F):
    direction=0;extreme=None;last=None;events=[];extime=None;anchor=None;anchor_t=None
    for row in a:
        t=int(row[0]);p=float(row[4])
        if last is None or t-last!=1:
            direction=0;extreme=p;extime=t;anchor=p;anchor_t=t
        elif direction==0:
            if abs(F.s.pct(p,extreme))>=.5:
                direction=1 if p>extreme else -1;extreme=p;extime=t
        elif (direction==1 and p<=extreme*.995) or (direction==-1 and p>=extreme*1.005):
            events.append({'minute':t,'pivotMinute':extime,'legStartMinute':anchor_t,
                           'completedLegPct':F.s.pct(extreme,anchor),'confirmationPct':F.s.pct(p,extreme),
                           'newDirection':-direction})
            anchor=extreme;anchor_t=extime;direction=-direction;extreme=p;extime=t
        elif (direction==1 and p>extreme) or (direction==-1 and p<extreme): extreme=p;extime=t
        last=t
    assert len(events)==F.reversal_count(a),'REVERSAL_WITNESS_PARITY'
    return events

def clauses(day,a,price,F):
    if not len(a): return {},{},[]
    terminal=F.s.pct(a[-1,4],price);eff=F.st.efficiency(a);rev=F.reversal_count(a)
    hit=a[a[:,2]>=price*1.01];dip=a[a[:,3]<=price*.995]
    h=int(hit[0,0]) if len(hit) else None;d=int(dip[0,0]) if len(dip) else None
    same=h is not None and h==d
    atoms={'DIRECT/hit':h is not None,'DIRECT/order':h is not None and (d is None or h<d),
           'DIRECT/terminal':terminal>=0,'DIRECT/efficiency':eff>=.2,
           'CHOP/reversals':rev>=4,'CHOP/efficiency':eff<=.3,
           'WEAKNESS/terminal':terminal<=-1,'WEAKNESS/below':float(np.mean(a[:,4]<price))>=.6,
           'WEAKNESS/recovery':F.c.ordered_oracle(a,int(a[0,0])).get('rangePct',100)<2}
    events=[]
    if h is not None: events.append({'kind':'FIRST_PLUS1_HIGH','minute':h})
    if d is not None: events.append({'kind':'FIRST_MINUS0_5_LOW','minute':d})
    low=None;lo_t=None;recovery_before=None;recovery=None
    for z in a:
        if low is not None and low<=price*.995 and z[2]>=low*1.02:
            witness={'lowMinute':lo_t,'highMinute':int(z[0]),'low':float(low),'high':float(z[2])}
            if recovery_before is None: recovery_before=witness
            if a[-1,4]>=low*1.01 and recovery is None: recovery=witness
        if low is None or z[3]<low: low=z[3];lo_t=int(z[0])
    regular=F.s.regular(day,a);counts=collections.Counter();before=None;cons=None
    for i in range(10,len(regular)):
        w=regular[i-10:i]
        if np.any(np.diff(w[:,0])!=1): continue
        counts['contiguous10']+=1
        high,low=max(w[:,2]),min(w[:,3]);mean=float(np.mean(w[:,2]-w[:,3]))
        if 100*(high-low)/w[0,1]>.6: continue
        counts['rangeLe0_6']+=1
        for j in range(i,min(i+10,len(regular))):
            z=regular[j]
            if z[0]-w[-1,0]!=j-i+1: break
            if z[4]<high*1.003: continue
            counts['breakoutClose']+=1
            if z[2]-z[3]<1.5*mean: continue
            counts['breakoutRange']+=1
            witness={'windowStart':int(w[0,0]),'windowEnd':int(w[-1,0]),'breakoutMinute':int(z[0]),'breakoutClose':float(z[4])}
            if before is None: before=witness
            if a[-1,4]>=z[4]:
                counts['terminalHeld']+=1
                if cons is None: cons=witness
    atoms.update({'RECOVERY/pairExists':recovery_before is not None,'RECOVERY/pairAndTerminal':recovery is not None,
                  'CONSOLIDATION/contiguous10':counts['contiguous10']>0,'CONSOLIDATION/compressed10':counts['rangeLe0_6']>0,
                  'CONSOLIDATION/breakoutClose':counts['breakoutClose']>0,'CONSOLIDATION/breakoutRange':before is not None,
                  'CONSOLIDATION/terminalHeld':cons is not None})
    for name,w in [('RECOVERY_PAIR',recovery_before),('RECOVERY_FULL',recovery)]:
        if w: events.extend([{'kind':name+'_LOW','minute':w['lowMinute']},{'kind':name+'_HIGH','minute':w['highMinute']}])
    for name,w in [('CONSOLIDATION_PRE_TERMINAL',before),('CONSOLIDATION_FULL',cons)]:
        if w: events.extend([{'kind':name+'_START','minute':w['windowStart']},{'kind':name+'_BREAKOUT','minute':w['breakoutMinute']}])
    detail={'sameBarHitDip':same,'recoveryBeforeTerminal':recovery_before,'recovery':recovery,
            'consolidationBeforeTerminal':before,'consolidation':cons,'consolidationCounts':dict(counts)}
    return atoms,detail,sorted(events,key=lambda x:(x['minute'],x['kind']))

def analyze(o,old,path,F):
    oid=o['id'];day=o['session'];start=int(old['start']);price=float(o['origin']['decisionPrice'])
    a=np.asarray(path['today'],float).reshape(-1,7)
    assert np.all(np.isfinite(a)) and (not len(a) or np.all(np.diff(a[:,0])>0)),'INVALID_RAW_PATH'
    assert not len(a) or np.all(a[:,1:5]>0),'NONPOSITIVE_OHLC'
    full=o['selectorOutcome']['mfeEnd'] is not None
    original=F.classify(day,start,price,a,full)
    assert original==old['pathEvaluatorOnly'],'ORIGINAL_CLASSIFICATION_MISMATCH:'+oid
    a=F.c.future_rows(day,a,start);ob=observation(day,start,a,full,F)
    sig='|'.join(k for k in PATHS[:-1] if original['predicate'][k]) or 'NONE'
    result={'opportunity':oid,'session':day,'symbol':o['symbol'],'start':start,'referencePrice':price,
            'original':original,'predicateSignature':sig,'chopOverride':original['path']==PATHS[3] and sum(original['predicate'].values())>1,
            'observation':ob,'metrics':{k:None for k in METRICS},'atoms':{},'witnesses':{},'events':[],'reversalEvents':[]}
    m=result['metrics'];m.update({k:ob[k] for k in ('rows','remainingActive','missingRegular')})
    if not len(a):return result,a
    lowrow=a[np.argmin(a[:,3])];highrow=a[np.argmax(a[:,2])];lo=float(lowrow[3]);hi=float(highrow[2]);last=float(a[-1,4])
    oracle=F.c.ordered_oracle(a,start);events=reversals_with_witness(a,F);amps=[abs(x['completedLegPct']) for x in events]
    regular=F.s.regular(day,a);segments=[]
    for z in regular:
        if segments and z[0]==segments[-1][-1][0]+1:segments[-1].append(z)
        else:segments.append([z])
    dif=[];logs=[];changes=0
    for sg in segments:
        closes=np.asarray(sg)[:,4];dv=np.diff(closes);dif.extend(dv);logs.extend(np.diff(np.log(closes)))
        signs=np.sign(dv[dv!=0]);changes+=int(np.sum(signs[1:]!=signs[:-1]))
    active=lambda t:sum(start<=v<int(t) for v in F.e.minutes(day))
    m.update(efficiency=F.st.efficiency(a),reversals=len(events),directionChanges=changes,terminalReturnPct=F.s.pct(last,price),
             rangePct=100*(hi-lo)/price,orderedRangePct=oracle.get('rangePct'),volatilityPct=float(np.std(logs)*100) if logs else None,
             closeLocation=(last-lo)/(hi-lo) if hi>lo else None,closingRecoveryPct=F.s.pct(last,lo),belowSelectorFraction=float(np.mean(a[:,4]<price)),
             swingAmplitudeMedianPct=float(np.median(amps)) if amps else None,swingAmplitudeMaxPct=max(amps) if amps else None,
             lowActiveDelay=active(lowrow[0]),highActiveDelay=active(highrow[0]),
             orderedLowActiveDelay=active(oracle['lowMinute']) if 'lowMinute' in oracle else None,
             orderedHighActiveDelay=active(oracle['highMinute']) if 'highMinute' in oracle else None,
             contiguousSegments=len(segments),longestSegment=max(map(len,segments)) if segments else 0,
             upMovePct=float(sum(v for v in dif if v>0)/price*100),downMovePct=float(-sum(v for v in dif if v<0)/price*100))
    atoms,witness,timeline=clauses(day,a,price,F)
    if original['reason'] not in ('INSUFFICIENT_OBSERVATION','MISSING_PATH_DATA'):
        assert bool(witness['recovery'])==original['predicate'][PATHS[1]],'RECOVERY_CLAUSE_PARITY'
        assert bool(witness['consolidation'])==original['predicate'][PATHS[2]],'CONSOLIDATION_CLAUSE_PARITY'
    witness.update(lowMinute=int(lowrow[0]),highMinute=int(highrow[0]),orderedOracle=oracle)
    result.update(atoms=atoms,witnesses=witness,events=timeline,reversalEvents=events)
    result['failedClauses']='|'.join(k for k,v in atoms.items() if not v) or 'NONE'
    return result,a

def representatives(rows):
    selected=collections.defaultdict(set);groups=collections.defaultdict(list)
    for r in rows:
        path=r['original']['path']
        if path in (PATHS[0],PATHS[2]):selected[r['opportunity']].add('ALL_RARE_'+path)
        if path==PATHS[-1]:groups['PATH6/'+str(r['original']['reason'])+'/'+r['predicateSignature']].append(r)
        if path==PATHS[3]:groups['CHOP/'+r['predicateSignature']].append(r)
    def pick(group,items,key):
        usable=[r for r in items if r['metrics'].get(key) is not None]
        if not usable:return
        ordered=sorted(usable,key=lambda r:(r['metrics'][key],r['opportunity']))
        med=float(np.median([r['metrics'][key] for r in ordered]))
        middle=min(ordered,key=lambda r:(abs(r['metrics'][key]-med),r['opportunity']))
        for name,r in [('MIN',ordered[0]),('MEDIAN',middle),('MAX',min((r for r in ordered if r['metrics'][key]==ordered[-1]['metrics'][key]),key=lambda r:r['opportunity']))]:
            selected[r['opportunity']].add(group+'/'+key+'/'+name)
    for g,items in sorted(groups.items()):
        pick(g,items,'efficiency' if any(r['metrics']['efficiency'] is not None for r in items) else 'remainingActive')
    pick('CHOP_ALL',[r for r in rows if r['original']['path']==PATHS[3]],'terminalReturnPct')
    return {k:sorted(v) for k,v in sorted(selected.items())}

def csvwrite(path,rows,fields):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)

def clock(t):return f'{int(t)//60:02d}:{int(t)%60:02d}'
def chart(path,r,a):
    width,height=1100,430;lft,top,pw,ph=72,82,980,285;ref=r['referencePrice'];start=r['start']
    end=max(start+1,int(a[-1,0]) if len(a) else start+1);yy=100*(a[:,1:5]/ref-1) if len(a) else np.zeros((1,4))
    ymin=min(0.,float(np.min(yy)));ymax=max(0.,float(np.max(yy)));pad=max(.15,(ymax-ymin)*.08);ymin-=pad;ymax+=pad
    x=lambda t:lft+(float(t)-start)/(end-start)*pw;y=lambda p:top+(ymax-float(p))/(ymax-ymin)*ph
    E=html.escape
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
         '<rect width="100%" height="100%" fill="white"/>',
         '<g font-family="sans-serif" font-size="12" fill="black">',
         f'<text x="20" y="22">{E(r["opportunity"])} | {E(r["original"]["path"])}</text>',
         f'<text x="20" y="42">Future anatomy only; no trades. Predicate: {E(r["predicateSignature"])}</text>',
         f'<text x="20" y="60">Gate: {E(r["observation"]["gateMask"])}; observed={len(a)}; regular missing={r["observation"]["missingRegular"]}</text>']
    if start<750 and end>690:
        xl=x(max(start,690));xr=x(min(end,750))
        out += [f'<rect x="{xl:.2f}" y="{top}" width="{max(0,xr-xl):.2f}" height="{ph}" fill="#eeeeee"/>',f'<text x="{xl+3:.2f}" y="{top+16}">Lunch</text>']
    for v in np.linspace(ymin,ymax,6):
        out += [f'<path d="M {lft} {y(v):.2f} H {lft+pw}" stroke="#dddddd"/>',f'<text x="5" y="{y(v)+4:.2f}">{v:.2f}%</text>']
    out.append(f'<path d="M {lft} {y(0):.2f} H {lft+pw}" stroke="black" stroke-dasharray="5 4"/>')
    chunks=[]
    for z in a:
        if chunks and z[0]==chunks[-1][-1][0]+1:chunks[-1].append(z)
        else:chunks.append([z])
        out.append(f'<path d="M {x(z[0]):.2f} {y(100*(z[3]/ref-1)):.2f} V {y(100*(z[2]/ref-1)):.2f}" stroke="#aaaaaa"/>')
    for ch in chunks:
        pts=' '.join(f'{x(z[0]):.2f},{y(100*(z[4]/ref-1)):.2f}' for z in ch)
        out.append(f'<polyline points="{pts}" fill="none" stroke="black" stroke-width="1.3"/>')
    for mark,minute in [('Low',r['witnesses'].get('lowMinute')),('High',r['witnesses'].get('highMinute'))]:
        if minute is not None:out.extend([f'<path d="M {x(minute):.2f} {top} V {top+ph}" stroke="black" stroke-dasharray="2 5"/>',f'<text x="{x(minute)+2:.2f}" y="{top+ph-7}">{mark}</text>'])
    for t in sorted({start,end,*range(((start+29)//30)*30,end,30)}):out.append(f'<text x="{x(t)-16:.2f}" y="{top+ph+20}">{clock(t)}</text>')
    ev='; '.join(clock(e['minute'])+' '+e['kind'] for e in r['events'])
    out.append(f'<text x="20" y="411">{E(ev[:165])}</text>')
    out.append('</g></svg>');path.parent.mkdir(parents=True,exist_ok=True);path.write_text('\n'.join(out)+'\n')

def coverage_chart(path,rows):
    times=sorted({r['start'] for r in rows})
    columns=('All','Insufficient','No dominant','Mixed','Insuff: missing 1m','Insuff: full unavail')
    w,h=1080,88+28*len(times);parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">','<rect width="100%" height="100%" fill="white"/>','<g font-family="sans-serif" font-size="12">','<text x="12" y="22">Selection clock x Path6 / coverage counts (last two columns overlap; not causal attribution)</text>']
    for j,label in enumerate(columns):parts.append(f'<text x="{115+155*j}" y="52">{label}</text>')
    for i,t in enumerate(times):
        rr=[r for r in rows if r['start']==t];ins=[r for r in rr if r['original']['reason']=='INSUFFICIENT_OBSERVATION']
        values=[len(rr),len(ins),sum(r['original']['reason']=='NO_DOMINANT_PATH' for r in rr),sum(r['original']['reason']=='TRUE_MIXED_PATH' for r in rr),sum(r['observation']['missingRegular']>0 for r in ins),sum(not r['observation']['fullSessionEvaluable'] for r in ins)]
        y=65+28*i;parts.append(f'<text x="12" y="{y+17}">{clock(t)}</text>')
        for j,n in enumerate(values):
            gray=int(248-130*n/max(1,len(rr)));parts.append(f'<rect x="{110+155*j}" y="{y}" width="145" height="24" fill="rgb({gray},{gray},{gray})"/><text x="{116+155*j}" y="{y+17}">{n}</text>')
    parts.append('</g></svg>');path.write_text('\n'.join(parts)+'\n')


def aggregate(rows):
    counts=dict(collections.Counter(r['original']['path'] for r in rows));reasons=dict(collections.Counter(r['original']['reason'] for r in rows if r['original']['path']==PATHS[-1]))
    assert counts==EXPECTED and reasons==REASONS,'POPULATION_RECONCILIATION'
    sufficient=[r for r in rows if r['original']['reason'] not in ('INSUFFICIENT_OBSERVATION','MISSING_PATH_DATA')]
    categories=collections.defaultdict(list)
    for r in rows:
        categories['PATH/'+r['original']['path']].append(r)
        if r['original']['path']==PATHS[-1]:categories['PATH6/'+r['original']['reason']].append(r)
        if r['original']['path']==PATHS[3]:categories['CHOP/'+r['predicateSignature']].append(r)
    dist={k:{m:distribution(r['metrics'][m] for r in rr) for m in METRICS} for k,rr in sorted(categories.items())}
    incidence={p:{'predicateTrue':sum(r['original']['predicate'][p] for r in sufficient),
                  'exclusiveAssigned':sum(r['original']['path']==p and sum(r['original']['predicate'].values())==1 for r in sufficient),
                  'mixedPath6':sum(r['original']['predicate'][p] and r['original']['reason']=='TRUE_MIXED_PATH' for r in sufficient),
                  'chopAbsorbed':sum(r['original']['predicate'][p] and r['chopOverride'] for r in sufficient)} for p in PATHS[:-1]}
    ins=[r for r in rows if r['original']['reason']=='INSUFFICIENT_OBSERVATION'];chop=[r for r in rows if r['original']['path']==PATHS[3]]
    cb=collections.Counter()
    for r in chop:
        ret=r['metrics']['terminalReturnPct'];rr=r['metrics']['orderedRangePct']
        band='LE_MINUS1' if ret<=-1 else 'MINUS1_TO0' if ret<0 else '0_TO1' if ret<1 else 'GE1'
        cb[band+'|'+('ORDERED_LT2' if rr<2 else 'ORDERED_GE2')+'|'+r['predicateSignature']]+=1
    return {'population':len(rows),'pathCounts':counts,'path6Reasons':reasons,'sufficientN':len(sufficient),
            'insufficientGateMasks':dict(collections.Counter(r['observation']['gateMask'] for r in ins)),
            'insufficientPrimaryReasons':dict(collections.Counter(r['observation']['primaryReason'] for r in ins)),
            'insufficientOverlappingFlags':{k:sum(bool(r['observation'][k]) for r in ins) for k in ('nearMorningEnd','nearAfternoonEnd','crossesLunch')},
            'insufficientFullUnavailable':sum(not r['observation']['fullSessionEvaluable'] for r in ins),
            'insufficientMissingRegular':sum(r['observation']['missingRegular']>0 for r in ins),
            'insufficientMissingTerminalAuction':sum(not r['observation']['terminalAuctionObserved'] for r in ins),
            'insufficientUnresolvedSourceCause':sum(r['observation']['sourceCause']=='UNRESOLVED_SOURCE_CAUSE' for r in ins),
            'predicateIncidence':incidence,'chopOverrideN':sum(r['chopOverride'] for r in rows),
            'chopSignatures':dict(collections.Counter(r['predicateSignature'] for r in chop)),
            'mixedCombinations':dict(collections.Counter(r['predicateSignature'] for r in rows if r['original']['reason']=='TRUE_MIXED_PATH')),
            'noDominantFailureSignatures':dict(collections.Counter(r['failedClauses'] for r in rows if r['original']['reason']=='NO_DOMINANT_PATH')),
            'atomicPassCounts':{k:sum(r['atoms'].get(k,False) for r in sufficient) for k in sorted({k for r in sufficient for k in r['atoms']})},
            'chopReturnRangeSignatures':dict(cb),'distributions':dist}

def report(summary,index):
    s=summary;lines=['# STEP 1 Future Path Deep Audit — STOP FOR HUMAN REVIEW','',
      'Reused Development; evaluator-only. Existing 5+1 labels are unchanged. No State, Signal, Entry, learning, Dictionary or EXIT evaluation.',
      '', '## Reconciliation','',f'All {s["population"]} IDs and every original classifier field reproduced exactly.',
      '', '| Original Path | Count |','|---|---:|']
    lines += [f'| {p} | {s["pathCounts"][p]} |' for p in PATHS]
    lines += ['', '## Observation insufficiency', '', 'Exact original gate failures (overlap retained):','', '```json',json.dumps(s['insufficientGateMasks'],indent=2),'```',
      f'Insufficient cases with missing regular minute stamps: {s["insufficientMissingRegular"]}; inherited full-session unavailable: {s["insufficientFullUnavailable"]}; terminal auction absent: {s["insufficientMissingTerminalAuction"]}.',
      f'Unresolved compact-source cause cases: {s["insufficientUnresolvedSourceCause"]}. Missing compact bars cannot distinguish no-trade, halt, filtering and provider loss. Lunch is not counted as missing trading minutes. Calendar and coverage co-occurrence does not prove causation.',
      '', '## Mixed paths and CHOP override','',f'{s["chopOverrideN"]} CHOP assignments also pass another original Path predicate. CHOP is therefore not automatically a pure, mutually exclusive motion type.',
      '','```json',json.dumps(s['mixedCombinations'],indent=2),'```','',
      'Mixed combinations here mean jointly true frozen predicates. Witness timestamps permit chronological inspection, but do not establish a causal State transition or intrabar ordering.',
      '', '## Rare Path clauses','', '| Predicate | True anywhere | Exclusive label | Mixed Path6 | CHOP absorbed |','|---|---:|---:|---:|---:|']
    for p,z in s['predicateIncidence'].items():lines.append(f'| {p} | {z["predicateTrue"]} | {z["exclusiveAssigned"]} | {z["mixedPath6"]} | {z["chopAbsorbed"]} |')
    lines += ['', 'Exclusive label counts are not the same as the frequency of the underlying predicate. atomicPassCounts in summary.json additionally separates structural breakouts/recoveries from the terminal condition. No threshold was changed.',
      '', '## NO_DOMINANT_PATH and CHOP shape', '',
      'All 355 no-dominant cases retain their exact failed-clause signatures, observed price paths, event witnesses and whole-path metrics. No passed predicate is a definition-level result, not proof of no movement.',
      'CHOP is tabulated by original predicate signature, net return band, ordered range, efficiency, amplitude, direction changes, volatility, low/high timing and recovery. See distributions and chopReturnRangeSignatures in summary.json. These are descriptive partitions, not newly trained or installed Path classes.',
      '', '## Evidence navigation', '',
      'raw/audit-records.json.gz: all 2,155 IDs with gates, metrics, clauses, witnesses and original labels.',
      'raw/future-paths.json.gz: all observed post-selection OHLCV/value rows used here; no interpolation.',
      'raw/observations.csv and selection-time.csv: per-ID and clock-time coverage/reason evidence.',
      'summary.json: full distributions, combinations and clause incidence; representatives.json and plots/index.md: deterministic chart selection.',
      f'{len(index)} representative charts; all 50 DIRECT and all 10 CONSOLIDATION labels are included, along with predeclared median/extreme representatives. Full population numerical outputs are not restricted to chart samples.',
      '', '## Completion gates', '', '| Gate | Status | Evidence / limitation |','|---|---|---|',
      '| 1 All 2,155 label counts explained | PASS | Exact original field replay and predicate incidence |',
      '| 2 Path6 989 reasons explained | PASS | 496/355/138 reconciled; raw gate masks and failed clauses |',
      '| 3 Insufficient 496 root causes | PARTIAL | Mechanical gate causes and observed gaps explained; provider/halt/no-trade provenance not available from compact rows |',
      '| 4 No-dominant 355 typical paths | PASS | Full metric/failure-signature records and deterministic charts; semantic interpretation requires human review |',
      '| 5 Mixed 138 combinations | PASS | All original combinations and chronological witnesses; concurrent predicates are not assumed sequential states |',
      '| 6 CHOP 828 single-group suitability | PARTIAL | Heterogeneity and absorption evidence recorded; not certified as one homogeneous semantic group |',
      '| 7 Keep/revise vocabulary decision | PARTIAL | Evidence ready for human review; no replacement vocabulary selected or installed |',
      '', '## Audit conclusion', '',
      'Do not treat 5+1 labels as a validated causal State vocabulary. Keep these historical labels immutable. Review observation availability separately from path semantics, and review whether overlapping events should be represented as sequences rather than forced single labels. This is an audit recommendation, not STEP 2 implementation.',
      '', 'STEP 1 evidence recorded with explicit limitations. STOP. Human review is required before deciding STEP 2; no later work is authorized. Dedicated CI success is not a claim that the entire PR is GREEN.',
      '', '## Safety', '',json.dumps(SAFETY,sort_keys=True),'',
      'providerRequests=0; holdoutOpened=0; training=false; statePrediction=false; entryTimingEvaluated=false; dictionaryUsed=false; exitResearch=false; nextStepStarted=false.']
    return '\n'.join(lines)+'\n'

def run(out,root=ROOT):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    inputs=[Path('scripts')/p for p in CODE]+[CONTRACT,SUB/'opportunities.json.gz',SUB/'raw-paths-evaluator-only.json.gz',OLD/'records.json.gz']
    pins={p.as_posix():pin(p,root=root) for p in inputs};pins[(BASE/'PROTOCOL.md').as_posix()]=pin(BASE/'PROTOCOL.md',PROTOCOL_COMMIT,root)
    contract=read(root/CONTRACT);ids=contract['opportunityIds'];allowed=set(contract['developmentSessions'])
    assert len(ids)==len(set(ids))==2155 and all(v is False for v in contract['safety'].values()),'CONTRACT'
    oldrows=read(root/OLD/'records.json.gz');previous={r['opportunity']:r for r in oldrows}
    assert len(previous)==len(oldrows)==2155 and set(previous)==set(ids),'ORIGINAL_ID_SET'
    allopps=read(root/SUB/'opportunities.json.gz')
    assert all(o['session'] in allowed for o in allopps),'OUTSIDE_DEVELOPMENT_SOURCE'
    idset=set(ids);selected=[o for o in allopps if o['id'] in idset];opps={o['id']:o for o in selected}
    assert len(selected)==len(opps)==2155 and set(opps)==set(ids),'OPPORTUNITY_SET'
    raw=read(root/SUB/'raw-paths-evaluator-only.json.gz');F=frozen(root);rows=[];paths={}
    for oid in sorted(ids):
        o=opps[oid];old=previous[oid]
        assert old['session']==o['session'] and old['symbol']==o['symbol'],'IDENTITY_MISMATCH'
        stamp=o['origin']['decisionTimestamp'];assert int(stamp[11:13])*60+int(stamp[14:16])==old['start'],'TIMESTAMP_MISMATCH'
        r,a=analyze(o,old,raw[oid],F);rows.append(r);paths[oid]={'session':o['session'],'columns':['minute','O','H','L','C','Vo','Va'],'rows':a.tolist()}
    summary=aggregate(rows);chosen=representatives(rows);index=[]
    for r in rows:
        oid=r['opportunity']
        if oid not in chosen:continue
        name=hashlib.sha256(oid.encode()).hexdigest()[:20]+'.svg';a=np.asarray(paths[oid]['rows'],float).reshape(-1,7)
        chart(out/'plots'/name,r,a);index.append({'opportunity':oid,'path':r['original']['path'],'reason':r['original']['reason'],'predicateSignature':r['predicateSignature'],'selection':chosen[oid],'file':'plots/'+name})
    write(out/'raw/audit-records.json.gz',rows);write(out/'raw/future-paths.json.gz',paths)
    write(out/'summary.json',summary);write(out/'representatives.json',index);write(out/'input-pins.json',pins)
    observations=[{'opportunity':r['opportunity'],'session':r['session'],'selectionTime':clock(r['start']),'path':r['original']['path'],'reason':r['original']['reason'],
                   'gateMask':r['observation']['gateMask'],**{k:r['observation'][k] for k in ('rows','remainingActive','missingRegular','fullSessionEvaluable','terminalAuctionObserved','nearMorningEnd','nearAfternoonEnd','crossesLunch')}} for r in rows]
    csvwrite(out/'raw/observations.csv',observations,list(observations[0]))
    counts=collections.Counter((r['start'],r['original']['path'],r['original']['reason'],r['observation']['gateMask']) for r in rows)
    table=[{'selectionTime':clock(k[0]),'path':k[1],'reason':k[2],'gateMask':k[3],'n':v} for k,v in sorted(counts.items(),key=lambda kv:tuple(str(x) for x in kv[0]))]
    csvwrite(out/'selection-time.csv',table,list(table[0]));coverage_chart(out/'selection-time.svg',rows)
    (out/'plots/index.md').write_text('# Deterministic representative charts\n\n'+''.join(f'- [{r["opportunity"]}]({Path(r["file"]).name}): {r["path"]}; {"; ".join(r["selection"])}\n' for r in index))
    (out/'REPORT.md').write_text(report(summary,index))
    write(out/'scope.json',{'referenceHead':REFERENCE,'protocolCommit':PROTOCOL_COMMIT,'safety':SAFETY,'providerRequests':0,'holdoutOpened':0,'training':False,'statePrediction':False,'entryTimingEvaluated':False,'dictionaryUsed':False,'exitResearch':False,'nextStepStarted':False,'status':'STEP1_EVIDENCE_WITH_LIMITATIONS_STOP_FOR_HUMAN'})
    write(out/'code-pins.json',{str(p.relative_to(root)):sha(p) for p in sorted((root/'scripts').glob('*future_path_deep_audit*.py'))})
    write(out/'manifest.json',{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    print(json.dumps({'population':len(rows),'pathCounts':summary['pathCounts'],'chopOverrideN':summary['chopOverrideN'],'plots':len(index),'status':'STOP_FOR_HUMAN'}))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args();run(args.output)
