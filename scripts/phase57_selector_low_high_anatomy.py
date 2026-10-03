"""Post-selection geometry only. Never an Entry/EXIT policy or executable return."""
from __future__ import annotations
import argparse, collections, datetime as dt, json, math, re, shutil, statistics
from pathlib import Path
from scripts import phase57_selector_pairability_v2 as v

a=v.a
ROOT=a.ROOT
BASE=ROOT/'docs/evidence/phase57-selector-low-high-anatomy-v1'
P=BASE/'02_protocol.json'
read,write,sha=a.read,a.write,a.sha
FIELDS=['selectionToLowPct','selectionToHighPct','lowToHighPct','sessionEndReturnPct']
ORDERS=['LOW_THEN_HIGH','HIGH_THEN_LOW','SAME_BAR_ORDER_UNKNOWN','NO_VALID_PATH']
PATTERNS=[f'down{d}_up{u}' for d in [1,2,3] for u in [3,5]]+[f'up{u}_giveback0' for u in [3,5]]
EPS=1e-10

def protocol():
    p=read(P)
    assert sha(P)==read(BASE/'protocol-lock.json')['protocolSHA256'],'PROTOCOL_HASH'
    assert p['id']=='PHASE57_POST_SELECTION_LOW_HIGH_PATH_ANATOMY_V1'
    assert p['frozen']['topK']==5
    assert len(p['safety'])==9 and all(x is False for x in p['safety'].values())
    assert not any(p['sealed'].values())
    for f,h in p['sourcePins'].items():assert sha(ROOT/f)==h,f
    return p

def members():
    m=read(a.MEMBERSHIP);lookup={r['selectorEventId']:r for r in m['new']};out={}
    allocation=read(ROOT/'predict/long-only/phase57-long-only-session-allocation-v3.json')
    allowed={d for k,days in allocation['partitions'].items() if k.startswith('DEVELOPMENT_') for d in days}
    for arm in a.ARMS[:2]:
        groups=collections.defaultdict(list)
        for i in m['arms'][arm]:groups[lookup[i]['decisionTimestamp']].append(i)
        assert len(groups)==760 and len(m['arms'][arm])==len(set(m['arms'][arm]))==3800
        out[arm]=[]
        for stamp,ids in groups.items():
            assert len(ids)==5
            if arm==a.ARMS[0]:assert ids==sorted(ids,key=lambda i:(-lookup[i]['savedV1Score'],lookup[i]['symbol']))
            for rank,i in enumerate(ids,1):
                r=lookup[i]
                assert r['sessionDate'] in allowed and r['decisionPrice']>75
                if arm==a.ARMS[0]:assert r['selectorRank']==rank
                out[arm].append({k:r[k] for k in ['selectorEventId','sessionDate','symbol','decisionTimestamp','decisionPrice','savedV1Score']}|{'originalRank':rank})
    assert [r['selectorEventId'] for r in out[a.ARMS[0]]]==m['arms'][a.ARMS[0]]
    return out

def trading_minutes(start,end):
    assert start.date()==end.date() and end>=start
    close=900 if str(start.date())<'2024-11-05' else 930
    def minute(t):return t.hour*60+t.minute+t.second/60
    lo,hi=minute(start),minute(end)
    return sum(max(0,min(hi,y)-max(lo,x)) for x,y in [(540,690),(750,close)])

def interval(bar,decision):
    return {'startJst':bar['start'].isoformat(),'endJst':bar['end'].isoformat(),
        'tradingMinutes':[trading_minutes(decision,bar[x]) for x in ['start','end']],
        'wallMinutes':[(bar[x]-decision).total_seconds()/60 for x in ['start','end']]}

def gap(first,second):
    return {clock:[max(0,second[clock][0]-first[clock][1]),second[clock][1]-first[clock][0]] for clock in ['tradingMinutes','wallMinutes']}

def ordered_pattern(bars,first,second,decision):
    left=[i for i,b in enumerate(bars) if first(b)];right=[i for i,b in enumerate(bars) if second(b)]
    pair=next(((i,j) for i in left for j in right if i<j),None)
    status='CONFIRMED' if pair else 'SAME_BAR_ORDER_UNKNOWN' if set(left)&set(right) else 'NOT_OBSERVED'
    return {'status':status,'firstThresholdReached':bool(left),'secondThresholdReached':bool(right),
        'witness':[interval(bars[i],decision) for i in pair] if pair else None}

def evaluate(path,member):
    for k in ['selectorEventId','sessionDate','symbol','decisionTimestamp','decisionPrice']:assert path[k]==member[k],k
    decision=a.old.timestamp(path['decisionTimestamp']);end=decision.replace(hour=15,minute=0 if path['sessionDate']<'2024-11-05' else 30)
    expected=a.regular_slots(decision,end);bars=a.old.materialize_path(path)
    raw={a.old.timestamp(b['start']):b for b in path['future']}
    for b in bars:
        assert b['start'] in expected and b['end']==b['start']+dt.timedelta(minutes=5),'NONREGULAR_OR_FUTURE_SESSION_BAR'
        if b['valid']:
            for k in ['o','h','l','c']:b[k]=float(raw[b['start']][k])
    mapping={b['start']:b for b in bars}
    missing=[{'startJst':t.isoformat(),'reason':'ABSENT_SLOT' if t not in mapping else 'MISSING_OR_INVALID_BAR'} for t in expected if t not in mapping or not mapping[t]['valid']]
    observed=[mapping[t] for t in expected if t in mapping and mapping[t]['valid']]
    r=member.copy()|{'status':'NO_VALID_PATH','reason':'NO_REGULAR_FUTURE_PATH' if not expected else 'INCOMPLETE_PATH' if missing else None,
        'order':'NO_VALID_PATH','expectedBars':len(expected),'validBars':len(observed),'missingBars':missing,
        'sparseObservedBars':sum((b.get('observedMinutes') or 0)<5 for b in observed),
        'remainingTradingMinutes':trading_minutes(decision,end),'remainingWallMinutes':(end-decision).total_seconds()/60,
        'lowHighOrderMeaning':'first attainment; repeated extrema retained; same-bar order unknown',
        **{k:None for k in FIELDS},'lowInterval':None,'highInterval':None,'lowToHighElapsed':None,'highToLowElapsed':None,
        'lowAttainmentIntervals':[],'highAttainmentIntervals':[],'firstHits':{str(t):None for t in [1,2,3,5]},
        'winner':{str(t):None for t in [1,2,3,5]},'patterns':{k:{'status':'NOT_EVALUABLE','firstThresholdReached':None,'secondThresholdReached':None,'witness':None} for k in PATTERNS}}
    if observed:
        lo=min(b['l'] for b in observed);hi=max(b['h'] for b in observed)
        r['partialObservedBounds']={'role':'BOUNDS_ONLY_NOT_FULL_SESSION_EXTREMA','lowUpperBoundPct':lo,'highLowerBoundPct':hi,'rangeLowerBoundPct':100*((1+hi/100)/(1+lo/100)-1)}
    else:r['partialObservedBounds']=None
    if not expected or missing:return r
    lows=[i for i,b in enumerate(observed) if b['l']==lo];highs=[i for i,b in enumerate(observed) if b['h']==hi]
    il,ih=lows[0],highs[0];low,high=interval(observed[il],decision),interval(observed[ih],decision)
    order='LOW_THEN_HIGH' if il<ih else 'HIGH_THEN_LOW' if ih<il else 'SAME_BAR_ORDER_UNKNOWN'
    r.update(status='VALID_COMPLETE_PATH',reason=None,order=order,selectionToLowPct=lo,selectionToHighPct=hi,
        lowToHighPct=100*((1+hi/100)/(1+lo/100)-1),sessionEndReturnPct=observed[-1]['c'],
        lowInterval=low,highInterval=high,lowAttainmentIntervals=[interval(observed[i],decision) for i in lows],
        highAttainmentIntervals=[interval(observed[i],decision) for i in highs],lowTieBars=len(lows),highTieBars=len(highs),
        lowPrice=path['decisionPrice']*(1+lo/100),highPrice=path['decisionPrice']*(1+hi/100),
        lowToHighElapsed=gap(low,high) if il<ih else None,highToLowElapsed=gap(high,low) if ih<il else None)
    for t in [1,2,3,5]:
        hit=next((b for b in observed if b['h']>=t-EPS),None)
        r['winner'][str(t)]=hit is not None;r['firstHits'][str(t)]=interval(hit,decision) if hit else None
    for d in [1,2,3]:
        for u in [3,5]:r['patterns'][f'down{d}_up{u}']=ordered_pattern(observed,lambda b:b['l']<=-d+EPS,lambda b:b['h']>=u-EPS,decision)
    for u in [3,5]:r['patterns'][f'up{u}_giveback0']=ordered_pattern(observed,lambda b:b['h']>=u-EPS,lambda b:b['l']<=EPS,decision)
    return r

def valid(rows):return [r for r in rows if r['status']=='VALID_COMPLETE_PATH']

def counts(rows):
    vv=valid(rows)
    return {'originalN':len(rows),'validN':len(vv),'invalidN':len(rows)-len(vv),
        'sessions':len({r['sessionDate'] for r in rows}),'validSessions':len({r['sessionDate'] for r in vv}),
        'uniqueSymbols':len({r['symbol'] for r in rows}),'validUniqueSymbols':len({r['symbol'] for r in vv}),
        'timestamps':len({r['decisionTimestamp'] for r in rows}),'validTimestamps':len({r['decisionTimestamp'] for r in vv}),
        'invalidReasons':dict(collections.Counter(r['reason'] for r in rows if r['reason']))}

def timing(rows):
    vv=valid(rows);out={}
    for field in ['lowInterval','highInterval','lowToHighElapsed','highToLowElapsed']:
        items=[r[field] for r in vv if r[field] is not None]
        out[field]={'eligibleN':len(items)}
        for clock in ['tradingMinutes','wallMinutes']:
            pairs=[x[clock] for x in items];n=len(pairs)
            out[field][clock]={'lowerBound':a.dist([x[0] for x in pairs]),'upperBound':a.dist([x[1] for x in pairs]),
                'cdf':{str(t):{'definiteBy':sum(x[1]<=t for x in pairs)/n if n else None,'possibleBy':sum(x[0]<=t for x in pairs)/n if n else None} for t in a.H},
                'sessionEndRate':1.0 if n else None}
    return out

def summarize(rows):
    vv=valid(rows);n=len(vv);c=collections.Counter(r['order'] for r in rows)
    return {'counts':counts(rows),'metrics':{f:a.dist([r[f] for r in vv]) for f in FIELDS},
        'orderCounts':{f:c[f] for f in ORDERS},'orderRatesAmongValid':{f:c[f]/n if n else None for f in ORDERS[:-1]},
        'timing':timing(rows),'role':'OBSERVED_COMPLETE_PATH_DESCRIPTIVE_NOT_FULL_POPULATION','lowToHighIsOracle':True}

def pattern_summary(rows,keys):
    vv=valid(rows);out={}
    for key in keys:
        c=collections.Counter(r['patterns'][key]['status'] for r in rows)
        first=sum(r['patterns'][key]['firstThresholdReached'] is True for r in vv)
        confirmed=c['CONFIRMED'];unknown=c['SAME_BAR_ORDER_UNKNOWN'];unobserved=len(rows)-len(vv)
        out[key]={'originalN':len(rows),'validN':len(vv),'firstThresholdN':first,'statuses':dict(c),
            'confirmedRateAmongValid':confirmed/len(vv) if vv else None,
            'confirmedRateAmongFirstThreshold':confirmed/first if first else None,
            'allOriginalLogicalRateBounds':[confirmed/len(rows),(confirmed+unknown+unobserved)/len(rows)] if rows else [None,None],
            'sameBarIsUnknown':True,'futureOutcomeConditioned':True}
    return out

def winner_comparison(rows,t):
    return {'thresholdPct':t,'futureOutcomeConditioned':True,'unknownN':len(rows)-len(valid(rows)),
        'winner':summarize([r for r in rows if r['winner'][str(t)] is True]),
        'nonwinner':summarize([r for r in rows if r['winner'][str(t)] is False]),
        'winnerPatterns':pattern_summary([r for r in rows if r['winner'][str(t)] is True],PATTERNS)}

def pair_comparison(left,right,full5):
    groups=[]
    for rows in [left,right]:
        g=collections.defaultdict(list)
        for r in valid(rows):g[r['decisionTimestamp']].append(r)
        groups.append(g)
    x,y=groups;stamps=sorted(x.keys()&y.keys())
    if full5:stamps=[t for t in stamps if len(x[t])==len(y[t])==5]
    result={'status':'EVALUABLE_DESCRIPTIVE' if stamps else 'NOT_EVALUABLE','reason':None if stamps else 'NO_ORIGINAL_FULL5_COMMON_COMPLETE_PATH_TIMESTAMP',
        'scope':'ORIGINAL_TOP5_COMPLETE_CASE' if full5 else 'OBSERVED_ORIGINAL_MEMBERS_AT_COMMON_TIMESTAMPS_ONLY',
        'timestamps':len(stamps),'sessions':len({t[:10] for t in stamps}),'selectorRows':sum(len(x[t]) for t in stamps),
        'randomRows':sum(len(y[t]) for t in stamps),'timestampSHA256':a.digest(stamps),'fullPopulationIdentified':False,'metrics':{}}
    for field in FIELDS[:3]+ORDERS[:2]:
        def value(r):return r[field] if field in FIELDS else float(r['order']==field)
        def means(g):
            days=collections.defaultdict(list)
            for t in stamps:days[t[:10]].append(statistics.mean(value(r) for r in g[t]))
            return {d:statistics.mean(z) for d,z in sorted(days.items())}
        s,b=means(x),means(y)
        result['metrics'][field]={'selector':v.cluster(s),'random':v.cluster(b),'difference':v.cluster({d:s[d]-b[d] for d in s})}
    return result

def emit(rows,random,out,paths_sha,code_hashes):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    for f in ['01_start_state.json','02_protocol.json','protocol-lock.json']:shutil.copy2(BASE/f,out/f)
    write(out/'03_selector_low_high_ledger.json.gz',{'role':'EVALUATOR_ONLY_ALL_ORIGINAL_ROWS','events':rows})
    write(out/'random-low-high-ledger.json.gz',{'role':'EVALUATOR_ONLY_ORIGINAL_RANDOM_NO_REDRAW','events':random})
    s=summarize(rows)
    for num,field,name in [(4,'selectionToLowPct','selection_to_low'),(5,'selectionToHighPct','selection_to_high'),(6,'lowToHighPct','low_to_high')]:
        write(out/f'{num:02}_{name}_summary.json',{'counts':s['counts'],'metric':s['metrics'][field],'scope':s['role'],'oracleOnly':field=='lowToHighPct',
            'bySession':{day:a.dist([r[field] for r in valid(rows) if r['sessionDate']==day]) for day in sorted({r['sessionDate'] for r in rows})}})
    write(out/'07_low_high_order_summary.json',{'counts':s['counts'],'orderCounts':s['orderCounts'],'orderRatesAmongValid':s['orderRatesAmongValid'],'tieSemantics':protocol()['order']})
    write(out/'08_low_high_timing.json',{'counts':s['counts'],'timing':s['timing'],'semantics':protocol()['timing']})
    comps={str(t):winner_comparison(rows,t) for t in [1,2,3,5]}
    write(out/'09_plus3_winner_anatomy.json',comps['3']);write(out/'10_plus5_winner_anatomy.json',comps['5'])
    write(out/'11_nonwinner_comparison.json',{'thresholds':comps,'invalidNeverNonwinner':True})
    ranks={str(k):summarize([r for r in rows if r['originalRank']==k]) for k in range(1,6)}
    write(out/'12_rank1_to_5_summary.json',{'ranks':ranks,'cutoffCreated':False,'sameMembership':True})
    down=pattern_summary(rows,PATTERNS[:6]);up=pattern_summary(rows,PATTERNS[6:])
    write(out/'13_down_then_rebound_thresholds.json',down);write(out/'14_up_then_giveback_thresholds.json',up)
    write(out/'15_path_archetypes.json',protocol()['archetypes']|{'alternative':'Quantitative order and ordered threshold signatures in files07/13/14; no new taxonomy.'})
    null={'primary':pair_comparison(rows,random,True),'observationConditional':pair_comparison(rows,random,False),
        'standaloneRandom':summarize(random),'seed':20260919,'repetitions':1,'newDraws':0,'futureAvailabilitySelection':False}
    write(out/'16_random_comparison.json',null)
    p=protocol()
    write(out/'20_safety.json',{'safety':p['safety'],'sealed':p['sealed'],'providerRequests':0,'fitCalls':0,'policyChanges':0,
        'originalSelector3800Preserved':True,'sourcePinsChecked':True,'fullUnionPathsSHA256':paths_sha,'newTrainingOrEntryExitRules':False})
    report=render(s,comps,ranks,down,up,null)
    (out/'21_final_report.md').write_text(report)
    (out/'22_final_handoff.md').write_text('# Final handoff — STOP\n\n'+report+'\n\nProtocol precommit: `225a6914611395cfe9a71c9da791d138fdca0a36`. Source start HEAD: `'+p['sourceHead']+'`. Producing HEAD and CI: 19_ci.json. No implementation, learning, Entry/EXIT/Capital changes or sealed-data opening. Next candidate is a proposal only.\n')
    write(out/'manifest.json',{'protocolSHA256':sha(P),'pathsSHA256':paths_sha,'code':code_hashes,
        'outputs':{f.name:sha(f) for f in sorted(out.iterdir())},'membershipSHA256':sha(a.MEMBERSHIP)})

def render(s,comps,ranks,down,up,null):
    def f(x):return 'N/A' if x is None else f'{x:.3f}'
    def pct(x):return 'N/A' if x is None else f'{100*x:.1f}%'
    n=s['counts'];lines=['# Frozen Selector Post-Selection Low/High Path Anatomy','',
        f"全{n['originalN']}行 / {n['sessions']} sessions。完全経路 {n['validN']}行 / {n['validSessions']} sessions / {n['validUniqueSymbols']} symbols。不完全{n['invalidN']}行はNO_VALID_PATHとして全行台帳に保持。",'',
        '**基準は選定時Decision Price。以下は完全観測経路に条件付けた記述で、元Top5全体の分布・実現利益・未知性能ではない。** min/maxを0でclampせず、low→highは時間順序を問わないoracle range。', '',
        '| metric % | mean | median | p05 | p10 | p25 | p75 | p90 | p95 |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for field,d in s['metrics'].items():lines.append('| '+field+' | '+' | '.join(f(d.get(k)) for k in ['mean','median','p05','p10','p25','p75','p90','p95'])+' |')
    lines+=['', '順序は最初に極値へ到達したバーで分類。極値の再到達区間も台帳保存。同一バー内順序は推測しない。']
    for k,rate in s['orderRatesAmongValid'].items():lines.append(f"- {k}: {s['orderCounts'][k]}行 / {pct(rate)}")
    lines+=['','## 時間','', '5分バーの区間で測定。下表は取引時間の下限・上限それぞれの中央値（分）。昼休みを除外。実経過時間とCDFの確定/可能範囲は08番。','', '| elapsed | lower median | upper median | n |','|---|---:|---:|---:|']
    for k,item in s['timing'].items():
        t=item['tradingMinutes'];lines.append(f"| {k} | {f(t['lowerBound']['median'])} | {f(t['upperBound']['median'])} | {item['eligibleN']} |")
    lines+=['','## Winner / nonwinner（将来条件付き）','', '| group | n | low median % | high median % | range median % | low→high rate | low upper median min | high upper median min | end median % |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for t in ['3','5']:
        for kind in ['winner','nonwinner']:
            z=comps[t][kind];m=z['metrics'];ti=z['timing'];lines.append(f"| +{t} {kind} | {z['counts']['validN']} | {f(m[FIELDS[0]]['median'])} | {f(m[FIELDS[1]]['median'])} | {f(m[FIELDS[2]]['median'])} | {pct(z['orderRatesAmongValid']['LOW_THEN_HIGH'])} | {f(ti['lowInterval']['tradingMinutes']['upperBound']['median'])} | {f(ti['highInterval']['tradingMinutes']['upperBound']['median'])} | {f(m[FIELDS[3]]['median'])} |")
    lines+=['','## 時間順序を要求した閾値イベント','', '閾値はすべて選定価格基準。別バーで先→後が確認できるものだけCONFIRMED。同一バーのみはUNKNOWN。大域的low/high順序とは異なり、途中の往復も検出する。','', '| pattern | confirmed | same-bar unknown | rate / valid | rate / first threshold | all-original bounds |','|---|---:|---:|---:|---:|---|']
    for k,z in (down|up).items():lines.append(f"| {k} | {z['statuses'].get('CONFIRMED',0)} | {z['statuses'].get('SAME_BAR_ORDER_UNKNOWN',0)} | {pct(z['confirmedRateAmongValid'])} | {pct(z['confirmedRateAmongFirstThreshold'])} | {', '.join(pct(x) for x in z['allOriginalLogicalRateBounds'])} |")
    lines+=['','## Original Rank 1〜5','', '| rank | original n | valid n | low median % | high median % | range median % | low→high rate |','|---|---:|---:|---:|---:|---:|---:|']
    for k,z in ranks.items():lines.append(f"| {k} | {z['counts']['originalN']} | {z['counts']['validN']} | {f(z['metrics'][FIELDS[0]]['median'])} | {f(z['metrics'][FIELDS[1]]['median'])} | {f(z['metrics'][FIELDS[2]]['median'])} | {pct(z['orderRatesAmongValid']['LOW_THEN_HIGH'])} |")
    p=null['primary'];c=null['observationConditional'];lines+=['','## Random','',f"元Top5全5銘柄同士: {p['status']} ({p['timestamps']} timestamps)。欠測を補完しない。補助の観測条件付き比較: {c['timestamps']} timestamps / {c['sessions']} sessions / Selector {c['selectorRows']}行 / Random {c['randomRows']}行。部分メンバー平均を元Top5成績と呼ばない。",'', '| metric | Selector | Random | difference | pointwise 95% CI |','|---|---:|---:|---:|---|']
    for k,z in c['metrics'].items():
        q=z['difference'];lines.append(f"| {k} | {f(z['selector']['sessionEqualMean'])} | {f(z['random']['sessionEqualMean'])} | {f(q['sessionEqualMean'])} | {q['clusterCI95']} |")
    lines+=['','CIはsession-cluster bootstrap、順序率は0〜1。他は%。日内timestamp・日間session等重み。5-session block感度もJSON保存。欠測バイアス・銘柄反復・既知Developmentへの過適合を消すものではない。','', '## 判断 / Q1〜Q10','',
        'Q1〜Q3: 典型値は上表のmedian/quantiles。Q4: 順序率は完全観測集合限定。Q5〜Q7: winner/nonwinnerのlow・high・時刻および閾値順序を参照。「即上昇」か「反発」かを未来極値からPIT判定できるとは言わない。Q8: rank別の記述差を保存しcutoffは作らない。']
    evidence=down['down1_up3']['statuses'].get('CONFIRMED',0)>0 and n['validN']>0
    lines+=[('Q9: 完全観測経路には、下落後の上昇という時間順序を確認できる事例が存在し、状態依存Entry/EXITの回収可能性を別診断する根拠はある。ただしoracle rangeを利益化できる根拠はまだない。' if evidence else 'Q9: 現在の観測集合から状態依存研究の根拠を十分に示せない。'),
        ('Q10 / 次工程候補: **A Causal Turning-Point / Entry Recoverability Diagnostic**。PIT情報だけで反発前の状態を識別できるか、固定nullと欠測契約の下で別途検証する。提案のみで未実行。' if evidence else 'Q10 / 次工程候補: **E INCONCLUSIVE**。追加実行なし。'),
        'B EXIT Recoverabilityは今回実行しない。C Economic Selector v2も実装しない。Dの追加取得・測定も未開始。任意archetype分類は新しい境界を追加しないためNOT_APPLICABLE、閾値イベントの定量記述を代わりに保存。','',
        '専用テスト・全回帰・CIの最終receiptは17/18/19番。Safety9項目false、既存Developmentのみ、DEV TEST/Fresh/OOS未開封、新規J-Quants0、Selector/Entry/EXIT/Capital変更0、main mergeなし。ここでSTOP。','']
    return '\n'.join(lines)

def measure(paths,out):
    p=protocol();assert sha(paths)==p['unionPathsSHA256'],'UNION_PATH_DRIFT'
    raw=read(paths);lookup={r['selectorEventId']:r for r in raw['events']};arms=members();results={}
    assert len(lookup)==11384
    selector_original={r['selectorEventId']:r for r in read(a.old.FROZEN_PATHS)['events']}
    for arm,mm in arms.items():
        results[arm]=[]
        for member in mm:
            path=lookup[member['selectorEventId']]
            if arm==a.ARMS[0]:assert path==selector_original[member['selectorEventId']],'SAVED_SELECTOR_PATH_PARITY'
            results[arm].append(evaluate(path,member))
    for arm,label in [(a.ARMS[0],'selector'),(a.ARMS[1],'random')]:
        prev=read(v.V1/f'{label}-path-ledger.json.gz')['events']
        expected={r['selectorEventId'] for r in prev if r['outcomes']['SESSION_END']['status']=='AVAILABLE'}
        assert {r['selectorEventId'] for r in valid(results[arm])}==expected,'COMPLETE_PATH_IDENTITY_DRIFT'
    code=['scripts/phase57_selector_low_high_anatomy.py','scripts/test_phase57_selector_low_high_anatomy.py','.github/workflows/phase57-selector-low-high-anatomy-v1.yml']
    emit(results[a.ARMS[0]],results[a.ARMS[1]],out,sha(paths),{f:sha(ROOT/f) for f in code})
    print(json.dumps({'status':'LOW_HIGH_ANATOMY_COMPLETE','counts':counts(results[a.ARMS[0]])}))

def audit(directory=None):
    p=protocol();members()
    if directory:
        d=Path(directory);m=read(d/'manifest.json');assert m['protocolSHA256']==sha(P) and m['pathsSHA256']==p['unionPathsSHA256']
        for f,h in m['outputs'].items():assert sha(d/f)==h,f
        for f,h in m['code'].items():assert sha(ROOT/f)==h,f
        ledger=read(d/'03_selector_low_high_ledger.json.gz')['events']
        assert len(ledger)==3800 and [r['selectorEventId'] for r in ledger]==read(a.MEMBERSHIP)['arms'][a.ARMS[0]]
        assert all(r['order']=='NO_VALID_PATH' and all(r[f] is None for f in FIELDS) for r in ledger if r['status']!='VALID_COMPLETE_PATH')
        if (d/'ci-manifest.json').exists():
            c=read(d/'ci-manifest.json');assert c['measurementManifestSHA256']==sha(d/'manifest.json')
            for f,h in c['outputs'].items():assert sha(d/f)==h,f
    print('LOW_HIGH_AUDIT_PASS')

def finalize(directory,regression,head,run_id):
    d=Path(directory);r=Path(regression);audit(d)
    log=(r/'targeted-tests.log').read_text();m=re.search(r'Ran (\d+) tests?',log);assert m and '\nOK' in log
    reg=read(r/'full/regression.json');assert reg['status']=='PASS'
    for f in ['17_tests.json','18_regression.json','19_ci.json','ci-manifest.json']:assert not (d/f).exists()
    write(d/'17_tests.json',{'status':'PASS','dedicatedTests':int(m[1]),'logSHA256':sha(r/'targeted-tests.log'),'deterministicRegeneration':'synthetic full-output byte parity tested; real measurements repeated in CI and artifact-manifest compared'})
    write(d/'18_regression.json',reg)
    write(d/'19_ci.json',{'measurement':'SUCCESS','regression':'SUCCESS','preservation':'RUNNING_AT_REPORT_CREATION_VERIFY_LINK_FOR_FINAL',
        'producingHead':head,'protocolPrecommit':'225a6914611395cfe9a71c9da791d138fdca0a36','runId':str(run_id),
        'url':f'https://github.com/Iam-2squared/ark-terminal/actions/runs/{run_id}','existingUnrelatedFailuresNotCleared':['EXIT CC Freeze Audit','Economic Alpha immutable-output guard']})
    write(d/'ci-manifest.json',{'measurementManifestSHA256':sha(d/'manifest.json'),'outputs':{f:sha(d/f) for f in ['17_tests.json','18_regression.json','19_ci.json']}})

def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('audit');p.add_argument('--directory')
    p=sub.add_parser('measure');p.add_argument('--paths',required=True);p.add_argument('--output-dir',required=True)
    p=sub.add_parser('finalize')
    for arg in ['directory','regression','head','run-id']:p.add_argument('--'+arg,required=True)
    args=ap.parse_args()
    if args.command=='audit':audit(args.directory)
    elif args.command=='measure':measure(args.paths,args.output_dir)
    else:finalize(args.directory,args.regression,args.head,args.run_id)

if __name__=='__main__':main()
