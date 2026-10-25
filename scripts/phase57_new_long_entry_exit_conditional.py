"""Saved Development-only conditional EXIT transfer. No Entry replay or tuning.

Run from repository root: python -m scripts.phase57_new_long_entry_exit_conditional
Consumes immutable saved opportunities, rebases saved OHLC, calls frozen EXIT.
"""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import gzip
import hashlib
import importlib.util
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/evidence/phase57-new-long-entry-exit-conditional-v1'
PATHS = 'docs/evidence/phase57-msh-entry-long-v2-development/paths.json.gz'
RUNTIME = 'predict/long-only/phase57_long_exit_continuation_v1.py'
INTERFACE = 'predict/long-only/phase57_long_exit_development_final.py'
ANCHOR_SHA = '985218fd1520bde127a72e9b049dd5a1840d42a928e7e850ea4e3e4d7ed82121'
HORIZONS = (5, 10, 15, 20, 30, 45, 60)
LEVELS = (1, 2, 3, 5)
SAFETY = {k: False for k in ('executionAllowed','brokerWriteAllowed',
    'excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed',
    'paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted')}
PINS = {
    PATHS: '9b051b630c1e5ac59fac42f0da32830f38e07c48ded56a26e2dec4c054a4b7ba',
    RUNTIME: 'b3e8f07086cfa65173524f62b78571f606e5d1c372a4cec1c16343c73d8c6c23',
    INTERFACE: 'd7b30e6a4419c10bf7cc2821b70159653af1cf0263d6abac09188c0f47a02a00',
    'docs/evidence/phase57-long-exit-continuation-v1/development-final.json':
        'e69b4257ec9a9895c939f873740924665fe8b00550bc6ea676054cf23c1f4460',
    'predict/research/phase57-long-only-frozen-selector-v1.json':
        'd93b3560f4be7dd231b88780f7d6d51cf8ecda85d4f599debcdd22c0c3feb5c8',
}
PARITY_PINS = {'ledger.ndjson.gz':'2286c023f6c53a2c73d67ad16eb51a57c8f2921cae0f749ada75e60af3f10002',
    'summary.json':'48a1dbea20da43f6fd3882e9b8ae26aa8b6403518d3fe533b385c435fa83cba7',
    'manifest.json':'c81dae9c4608373bbda20484034abbedb5362d01c92f08f9cbb9a45273a709f2'}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def encoded(x): return (json.dumps(x,sort_keys=True,allow_nan=False,separators=(',',':'))+'\n').encode()
def read(p):
    p = Path(p); b = p.read_bytes()
    if p.suffix == '.gz': b = gzip.decompress(b)
    return [json.loads(v) for v in b.splitlines()] if 'ndjson' in p.name else json.loads(b)
def write(p, x):
    b = encoded(x)
    if str(p).endswith('.gz'): b = gzip.compress(b,mtime=0)
    Path(p).write_bytes(b)
def module(name, path):
    s=importlib.util.spec_from_file_location(name,ROOT/path)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def minute(s):
    t=dt.datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(dt.timezone(dt.timedelta(hours=9)))
    assert t.second==0 and t.microsecond==0
    return t.hour*60+t.minute
def stamp(session, m): return f'{session}T{m//60:02d}:{m%60:02d}:00+09:00'
def regular(m,end): return 540<=m<end and not 690<=m<750
def grid(start,end): return [m for m in range(start,end,5) if regular(m,end)]
def segment_end(m,end): return 690 if 540<=m<690 else end if 750<=m<end else None
def valid(b):
    return b is not None and not b.get('missing') and all(
        isinstance(b.get(k),(int,float)) and not isinstance(b[k],bool)
        and math.isfinite(b[k]) for k in ('o','h','l','c'))
def quantile(a,p):
    if not a:return None
    a=sorted(a);i=(len(a)-1)*p;lo=math.floor(i);hi=math.ceil(i)
    return a[lo]+(a[hi]-a[lo])*(i-lo)
def dist(a):
    a=[x for x in a if x is not None]
    return {'n':len(a),'mean':statistics.mean(a) if a else None,
        'median':quantile(a,.5),'p05':quantile(a,.05),'p95':quantile(a,.95),
        'worst5Mean':statistics.mean(sorted(a)[:max(1,math.ceil(len(a)*.05))]) if a else None,
        'min':min(a) if a else None,'max':max(a) if a else None}
def rate(n,d): return {'n':n,'denominator':d,'rate':n/d if d else None}

def adapt(op,path):
    """Only mechanical timestamp/price rebase. Never emit or change an Entry event."""
    if op.get('referenceStatus')!='REFERENCE_OPEN':
        return {'status':'INELIGIBLE_REFERENCE','reason':op.get('referenceStatus')}
    price=op.get('referencePrice')
    assert isinstance(price,(int,float)) and math.isfinite(price) and price>0
    ts=op.get('referenceTimestamp') or op['opportunityTimestamp']
    assert dt.datetime.fromisoformat(ts)>=dt.datetime.fromisoformat(op['opportunityTimestamp'])
    start=minute(ts);end=path['sessionEndMinute'];session=path['sessionDate']
    assert ts[:10]==session and regular(start,end)
    source={minute(b['start']):b for b in path['future']}
    assert len(source)==len(path['future'])
    first=source.get(start)
    assert valid(first) and dt.datetime.fromisoformat(first['start'])==dt.datetime.fromisoformat(ts)
    assert math.isclose(path['decisionPrice']*(1+first['o']/100),price,rel_tol=1e-12)
    bars=[]
    for i,m in enumerate(grid(start,end)):
        b=source.get(m);missing=not valid(b)
        row={'slot':i+1,'start':stamp(session,m),'end':stamp(session,m+5),
             'minutes':m+5-start,'missing':missing,'observedMinutes':None if b is None else b.get('observedMinutes')}
        if not missing:
            assert minute(b['end'])==m+5
            for k in ('o','h','l','c'):row[k]=100*(path['decisionPrice']*(1+b[k]/100)/price-1)
            assert row['l']<=min(row['o'],row['c'])+1e-8 and row['h']+1e-8>=max(row['o'],row['c'])
        bars.append(row)
    return {'status':'REFERENCE_POSITION','positionStartTimestamp':ts,'startMinute':start,
        'sessionEndMinute':end,'direction':'LONG','expectedBars':len(bars),'future':bars,
        'fillPriceAssumption':price,'fillSemantics':'SCHEDULED_OPEN_REFERENCE_NOT_EXECUTION'}

def evaluate_window(rows):
    if not rows:return {'status':'EMPTY_WINDOW'}
    if any(b['missing'] for b in rows):return {'status':'UNKNOWN_MISSING_BAR'}
    hi=max(rows,key=lambda b:b['h']);lo=min(rows,key=lambda b:b['l'])
    mfe=max(0,hi['h']);mae=min(0,lo['l']);close=rows[-1]['c']
    first_adverse=next((b for b in rows if b['l']<0),None)
    def later_recovery(b):
        return next((x for x in rows if b and x['slot']>b['slot'] and x['c']>=0),None)
    recovery=later_recovery(first_adverse);worst_recovery=later_recovery(lo) if mae<0 else None
    def interval(b):return {'start':b['start'],'end':b['end'],'clockMinutesStart':b['minutes']-5,'clockMinutesEnd':b['minutes']}
    downside={}
    for k in (2,5):
        hit=next((b for b in rows if b['l']<=-k),None);rec=later_recovery(hit)
        downside[str(k)]={'hit':hit is not None,'hitBar':hit['slot'] if hit else None,
            'recoveredLaterClose':rec is not None,'recoveryClockMinutes':rec['minutes'] if rec else None,
            'winner3AfterDeepAdverse':bool(hit and any(b['slot']>hit['slot'] and b['h']>=3 for b in rows)),
            'winner5AfterDeepAdverse':bool(hit and any(b['slot']>hit['slot'] and b['h']>=5 for b in rows)),
            'failedDipNegativeFinalClose':bool(hit and close<0)}
    return {'status':'COMPLETE','bars':len(rows),'closePct':close,'mfePct':mfe,'maePct':mae,
        'worstAdversePct':mae,'mfeInterval':interval(hi) if mfe>0 else None,
        'maeInterval':interval(lo) if mae<0 else None,
        'firstPositiveCloseMinutes':next((b['minutes'] for b in rows if b['c']>0),None),
        'adverse':first_adverse is not None,'adverseRecoveredLaterClose':recovery is not None,
        'adverseRecoveryClockMinutes':recovery['minutes'] if recovery else None,
        'adverseRecoveryDelayUpperMinutes':recovery['minutes']-(first_adverse['minutes']-5) if recovery else None,
        'worstAdverseRecoveredLaterClose':worst_recovery is not None,
        'worstRecoveryClockMinutes':worst_recovery['minutes'] if worst_recovery else None,
        'givebackPP':mfe-close,'reach':{str(k):mfe>=k for k in LEVELS},
        'firstHitBars':{str(k):next((b['slot'] for b in rows if b['h']>=k),None) for k in LEVELS},
        'downside':downside,'fullUnderlyingMinutes':all(b['observedMinutes']==5 for b in rows)}

def path_diagnostic(e,session):
    if e['status']!='REFERENCE_POSITION':return {str(h):{'status':e['reason']} for h in (*HORIZONS,'SAFE_REGULAR_END')}
    out={};start=e['startMinute'];end=e['sessionEndMinute'];bound=segment_end(start,end)
    for h in HORIZONS:
        out[str(h)]=({'status':'UNKNOWN_SEGMENT_BOUNDARY'} if bound is None or start+h>bound
                    else evaluate_window([b for b in e['future'] if b['minutes']<=h]))
    safe_end=900 if session<'2024-11-05' else 925
    out['SAFE_REGULAR_END']=evaluate_window([b for b in e['future'] if minute(b['end'])<=safe_end])
    return out

def replay_existing(e,final):
    if e['status']!='REFERENCE_POSITION':return {'status':'INELIGIBLE_REFERENCE','reason':e['reason'],'netPct':None}
    if not e['expectedBars']:return {'status':'CENSORED','reason':'NO_REMAINING_REGULAR_BAR','netPct':None}
    state=final.new_position(e['expectedBars'])
    for b in e['future']:
        # Decision payload deliberately excludes OHLC HIGH/LOW and evaluation labels.
        payload={k:b[k] for k in ('slot','missing','end','minutes')}
        if not b['missing']:payload['c']=b['c']
        r=final.on_completed_bar(state,payload)
        if r['status']!='HOLD_RESEARCH_STATE':return r
    return {'status':'CENSORED','reason':'INCOMPLETE_TO_CALENDAR_CAP','netPct':None}

def enrich(result,e):
    if result['status']=='EXIT_REFERENCE':
        r=dict(result);r['preExitPath']=evaluate_window(e['future'][:r['exitBar']]);return r
    return result
def drawdown(values):
    equity=peak=0.;dd=0.
    for v in values:equity+=v;peak=max(peak,equity);dd=min(dd,equity-peak)
    return dd if values else None

def performance(rows,arm):
    rs=[r for r in rows if r[arm]['status']=='EXIT_REFERENCE'];a=[r[arm]['netPct'] for r in rs]
    profits=sum(x for x in a if x>0);loss=-sum(x for x in a if x<0)
    refs=[r['fixed']['preExitPath'] for r in rs]
    cap=[r[arm]['grossPct']/p['mfePct'] for r,p in zip(rs,refs) if p['mfePct']>0]
    by_entry=sorted(rs,key=lambda r:(r['positionStartTimestamp'],r['anchorId']))
    by_exit=sorted(rs,key=lambda r:(r[arm]['exitTimestamp'],r['anchorId']))
    out={'n':len(rs),'netSumPP':sum(a) if a else None,'netPct':dist(a),
        'winRate':rate(sum(x>0 for x in a),len(a)),'pf':profits/loss if loss else None,
        'pfStatus':'DEFINED' if loss else 'NO_NEGATIVE_TRADES',
        'entryOrderDDProxyPP':drawdown([r[arm]['netPct'] for r in by_entry]),
        'exitOrderDDProxyPP':drawdown([r[arm]['netPct'] for r in by_exit]),
        'holdingBars':dist([r[arm]['exitBar'] for r in rs]),
        'holdingClockMinutes':dist([r[arm]['holdingClockMinutes'] for r in rs]),
        'reasons':dict(collections.Counter(r[arm]['reason'] for r in rs)),
        'mfeCapture':dist(cap),'givebackPP':dist([p['mfePct']-r[arm]['grossPct'] for r,p in zip(rs,refs)]),
        'preExitMaePct':dist([r[arm]['preExitPath']['maePct'] for r in rs]),'winners':{}}
    for k in LEVELS:
        winners=[r for r in rs if r['fixed']['preExitPath']['mfePct']>=k]
        out['winners'][str(k)]={'n':len(winners),
            'finalNetPositive':rate(sum(r[arm]['netPct']>0 for r in winners),len(winners)),
            'finalNetAtLeastLevel':rate(sum(r[arm]['netPct']>=k for r in winners),len(winners)),
            'exitBeforeFirstHighTouch':rate(sum(r[arm]['exitBar']<r['fixed']['preExitPath']['firstHitBars'][str(k)] for r in winners),len(winners))}
    return out

def comparison(rows):
    paired=[r for r in rows if all(r[k]['status']=='EXIT_REFERENCE' for k in ('fixed','existing'))]
    delta=[r['existing']['netPct']-r['fixed']['netPct'] for r in paired]
    out={'population':len(rows),'pairedN':len(paired),
        'fixed':performance(paired,'fixed'),'existing':performance(paired,'existing'),
        'netDeltaPP':sum(delta) if delta else None,'deltaPct':dist(delta),
        'savedNetWinners':sum(r['existing']['netPct']>0>=r['fixed']['netPct'] for r in paired),
        'lostNetWinners':sum(r['fixed']['netPct']>0>=r['existing']['netPct'] for r in paired),
        'deltaRemovingLargestImprovementPP':sum(delta)-max(delta) if delta else None}
    return out

def path_summary(rows):
    out={}
    for h in (*map(str,HORIZONS),'SAFE_REGULAR_END'):
        valid_rows=[r['path'][h] for r in rows if r['path'][h]['status']=='COMPLETE']
        adverse=[p for p in valid_rows if p['adverse']]
        out[h]={'n':len(valid_rows),'population':len(rows),
            'statuses':dict(collections.Counter(r['path'][h]['status'] for r in rows)),
            **{k:dist([r[k] for r in valid_rows]) for k in ('closePct','mfePct','maePct','givebackPP',
                'firstPositiveCloseMinutes','adverseRecoveryClockMinutes','adverseRecoveryDelayUpperMinutes','worstRecoveryClockMinutes')},
            'timeToMFEIntervalEnd':dist([r['mfeInterval']['clockMinutesEnd'] for r in valid_rows if r['mfeInterval']]),
            'timeToMAEIntervalEnd':dist([r['maeInterval']['clockMinutesEnd'] for r in valid_rows if r['maeInterval']]),
            'adverseRecovery':rate(sum(r['adverseRecoveredLaterClose'] for r in adverse),len(adverse)),
            'reach':{str(k):rate(sum(r['reach'][str(k)] for r in valid_rows),len(valid_rows)) for k in LEVELS},
            'deepAdverse':{}}
        for k in (2,5):
            ds=[r['downside'][str(k)] for r in valid_rows if r['downside'][str(k)]['hit']]
            out[h]['deepAdverse'][str(k)]={'count':len(ds),**{key:rate(sum(r[key] for r in ds),len(ds)) for key in
                ('recoveredLaterClose','winner3AfterDeepAdverse','winner5AfterDeepAdverse','failedDipNegativeFinalClose')}}
    return out

def run(outdir):
    for p,h in PINS.items():assert sha(ROOT/p)==h,p
    for p,h in PARITY_PINS.items():assert sha(BASE/'entry-parity'/p)==h,p
    # Verify the frozen interface's own complete source/evidence/upstream receipt.
    frozen=read(ROOT/'docs/evidence/phase57-long-exit-continuation-v1/development-final.json')
    for p,h in {**frozen['evidencePins'],**frozen['upstreamPins']}.items():assert sha(ROOT/p)==h,p
    source=read(ROOT/PATHS)
    assert source['providerRequests']==0 and source['freshAccess']==0 and source['oosAccess']==0
    paths={e['selectorEventId']:e for e in source['events']}
    entries=read(BASE/'entry-parity/ledger.ndjson.gz')
    ids=sorted(r['anchorId'] for r in entries)
    assert len(ids)==2743 and len(set(ids))==2743
    assert hashlib.sha256(('\n'.join(ids)+'\n').encode()).hexdigest()==ANCHOR_SHA
    assert sum(r['evaluator']['primary60'] for r in entries)==878
    runtime=module('conditional_frozen_runtime',RUNTIME);final=module('conditional_frozen_final',INTERFACE)
    ledger=[]
    for entry in entries:
        for key in ('initialEvent','secondaryEvent'):
            op=entry['decision'][key]
            if op is None:continue
            p=paths[entry['anchorId']]
            assert op['anchorId']==p['selectorEventId'] and op['symbol']==p['symbol'] and op['session']==p['sessionDate']
            e=adapt(op,p);ev=entry['evaluator'];row={
                'anchorId':entry['anchorId'],'symbol':entry['symbol'],'sessionDate':entry['sessionDate'],
                'opportunity':op,'cohort':op['eventType'],'primary60':ev['primary60'],
                'referenceStatus':e['status'],'referenceReason':e.get('reason'),
                'positionStartTimestamp':e.get('positionStartTimestamp'),
                'fillPriceAssumption':e.get('fillPriceAssumption'),
                'path':path_diagnostic(e,entry['sessionDate'])}
            row['existing']=enrich(replay_existing(e,final),e)
            row['fixed']=enrich(runtime.replay(e,'FIXED12'),e) if e['status']=='REFERENCE_POSITION' else dict(row['existing'])
            row['riskTags']=[]
            if key=='secondaryEvent' and ev['primary60'] and ev.get('buyImprovementPct',0)>0:
                row['riskTags'].append('CHEAPER_PRIMARY_299')
                for k in (2,5):
                    if ev['secondaryD30']['downside']>=k:row['riskTags'].append(f'CHEAPER_PRIMARY_D30_{k}')
            row['riskExitTiming']={}
            for k in (2,5):
                d=row['path']['30'];r=row['existing']
                hit=d['downside'][str(k)]['hitBar'] if d['status']=='COMPLETE' else None
                row['riskExitTiming'][str(k)]=( 'UNKNOWN' if hit is None or r['status']!='EXIT_REFERENCE' else
                    'BEFORE_ADVERSE_BAR' if r['exitBar']<hit else 'SAME_BAR_ORDER_UNKNOWN' if r['exitBar']==hit else 'AFTER_ADVERSE_BAR')
            ledger.append(row)
    summary={'schemaVersion':1,'status':'CONDITIONAL_REFERENCE_DIAGNOSTIC_NOT_VALIDATED',
        'startHead':'efa7efb5235dcb1b711599d5c0ba0a196ec5fab9','anchorIdentitySHA256':ANCHOR_SHA,
        'entryReplay':False,'newExitPolicy':False,'safety':SAFETY,'cohorts':{},'riskSubsets':{}}
    for cohort in ('INITIAL_ENTRY_OPPORTUNITY','DIP_REPRICE_OPPORTUNITY'):
        rows=[r for r in ledger if r['cohort']==cohort]
        summary['cohorts'][cohort]={
            'opportunities':len(rows),'referenceEligible':sum(r['referenceStatus']=='REFERENCE_POSITION' for r in rows),
            'existingStatuses':dict(collections.Counter(r['existing']['status']+':'+r['existing']['reason'] for r in rows)),
            'existingStandaloneN':sum(r['existing']['status']=='EXIT_REFERENCE' for r in rows),
            'fixedStandaloneN':sum(r['fixed']['status']=='EXIT_REFERENCE' for r in rows),
            'paired':comparison(rows),'primary60Subset':comparison([r for r in rows if r['primary60']]),
            'fullUnderlyingMinutesPaired':comparison([r for r in rows if r['fixed'].get('preExitPath',{}).get('fullUnderlyingMinutes')]),
            'path':path_summary(rows)}
    for tag,n in [('CHEAPER_PRIMARY_299',299),('CHEAPER_PRIMARY_D30_2',106),('CHEAPER_PRIMARY_D30_5',21)]:
        rows=[r for r in ledger if tag in r['riskTags']];assert len(rows)==n,(tag,len(rows))
        subset=comparison(rows);subset['path']=path_summary(rows)
        subset['exitTiming']={str(k):dict(collections.Counter(r['riskExitTiming'][str(k)] for r in rows)) for k in (2,5)}
        subset['allIdentities']=[r['anchorId'] for r in rows]
        summary['riskSubsets'][tag]=subset
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    write(outdir/'summary.json',summary);write(outdir/'ledger.json.gz',ledger)
    # Reproducibility receipt covers exact upstream data, input events and evaluator.
    inputpins={**PINS,**{str((BASE/'entry-parity'/p).relative_to(ROOT)):h for p,h in PARITY_PINS.items()}}
    for p in [Path(__file__),BASE/'contract.md']:inputpins[str(p.relative_to(ROOT))]=sha(p)
    write(outdir/'manifest.json',{'schemaVersion':1,'inputPins':inputpins,
        'outputPins':{p:sha(outdir/p) for p in ('summary.json','ledger.json.gz')},
        'anchorIdentitySHA256':ANCHOR_SHA,'unit':'conditional unweighted reference return; not portfolio',
        'zeroCounters':{k:0 for k in ('entryReplay','entryChanges','selectorChanges','allocationChanges',
            'exitRuleChanges','modelFit','analogBuild','providerRequests','freshAccess','oosAccess','mainMerge')},'safety':SAFETY})
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',default=str(BASE));args=parser.parse_args()
    s=run(args.out)
    print(json.dumps({k:{'opportunities':v['opportunities'],'referenceEligible':v['referenceEligible'],
        'pairedN':v['paired']['pairedN'],'fixedMean':v['paired']['fixed']['netPct']['mean'],
        'existingMean':v['paired']['existing']['netPct']['mean']} for k,v in s['cohorts'].items()},indent=2))
