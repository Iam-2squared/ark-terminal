"""Causal prior-day State9 adapter; frozen upstream source is read-only.

Uses pinned RC2 rules, M0 Decimal80 coordinates and a Decimal120 check.
It does not fit/retune a dictionary, admit carried states or modify State9.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import sys
from pathlib import Path
from decimal import Decimal,Context,localcontext,ROUND_HALF_EVEN,InvalidOperation,DivisionByZero,Overflow
from functools import lru_cache
from collections import Counter

from preopen_io import private_path,verify_entry,write_json,sha_file,SAFE_FLAGS,utc_now
from preopen_selector import PreopenError,digest,stamp
from preopen_native_source import cash_clock
from preopen_compact_source import CompactNativeStore

Q=Decimal('1e-24')

def decimal_context(precision):
    ctx=Context(prec=precision,rounding=ROUND_HALF_EVEN,Emin=-999999,Emax=999999,clamp=0)
    for signal in ctx.traps:ctx.traps[signal]=signal in (InvalidOperation,DivisionByZero,Overflow)
    return ctx

@lru_cache(maxsize=150000)
def _logarithm(text,precision):
    import re
    if type(text) is not str or re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?',text,re.ASCII) is None:
        raise PreopenError('STATE_RAW_DECIMAL_LEXEME')
    value=Decimal(text)
    if not value.is_finite() or value<=0:raise PreopenError('STATE_NONPOSITIVE_PRICE')
    with localcontext(decimal_context(precision)) as ctx:
        ctx.clear_flags();result=value.ln()
        return result,tuple(s for s,v in ctx.flags.items() if v)

def normalized_coordinates(previous,current,precision):
    """Memoized exact logarithms; cached calls propagate Decimal status flags."""
    with localcontext(decimal_context(precision)) as ctx:
        ctx.clear_flags()
        def ln(text):
            v,flags=_logarithm(text,precision)
            for s in flags:ctx.flags[s]=True
            return v
        p=sorted(previous,key=lambda r:r['Time'])
        def minute(r):return int(r['Time'][:2])*60+int(r['Time'][3:5])
        stop=925 if p[0]['Date']>='2024-11-05' else 900
        opening_am=min((minute(r) for r in p if 540<=minute(r)<690),default=None)
        opening_pm=min((minute(r) for r in p if 750<=minute(r)<stop),default=None)
        changes=[]
        for left,right in zip(p,p[1:]):
            a,b=minute(left),minute(right)
            if b-a!=1 or a in (opening_am,opening_pm) or b in (opening_am,opening_pm):continue
            if not (540<=a<b<690 or 750<=a<b<stop):continue
            changes.append(abs(ln(right['C'])-ln(left['C'])))
        if not changes:raise PreopenError('STATE_SCALE_INSUFFICIENT_LOOKBACK')
        changes.sort();n=len(changes)
        median=changes[n//2] if n%2 else (changes[n//2-1]+changes[n//2])/Decimal(2)
        unit=max(ln('1.001'),Decimal('0.5')*median).quantize(Q)
        origin=ln(p[-1]['C'])
        coords=[{k:format(((ln(r[k])-origin)/unit).quantize(Q),'f') for k in ('O','H','L','C')} for r in current]
        return {'U':format(unit,'f'),'P_ref':p[-1]['C'],'previous_return_pairs_N':n,
                'coordinates':coords,'flags':{s.__name__:bool(v) for s,v in ctx.flags.items()}}

def pinned_upstream(contract,root):
    files={n:verify_entry(e,root) for n,e in contract['files'].items()}
    if (contract.get('reviewed') is not True or set(files)!=
            {'api.py','exact.py','kernel.py','normalize80.py','normalize120.py','profile.json','RC2_CONTRACT.txt','M0.md'}):
        raise PreopenError('STATE_FROZEN_SOURCE_CONTRACT')
    directory=files['api.py'].parent.parent
    for n in ('api.py','exact.py','kernel.py'):
        if files[n]!=directory/'candidate'/n:raise PreopenError('STATE_SOURCE_PACKAGE_LAYOUT')
    sys.path.insert(0,str(directory))
    from candidate.api import Engine
    from candidate.kernel import Bar
    from candidate.exact import parse
    import normalize80,normalize120
    return files,Engine,Bar,parse,normalize80,normalize120

def terminal_segment(rows,session):
    """Only last continuous segment; kernel resets at every known interval gap."""
    close=cash_clock(session)['continuous_close']
    end=int(close[:2])*60+int(close[3:])
    pairs=[(int(r['Time'][:2])*60+int(r['Time'][3:5]),r) for r in rows]
    pm=[(t,r) for t,r in pairs if 750<=t<end]
    if not pm or pm[-1][0]+1!=end:return []
    opening=pm[0][0]
    segment=[];last=None
    for t,r in pm:
        if t==opening:continue
        if last is not None and t!=last+1:segment=[]
        segment.append(r);last=t
    return segment

def generate_state_ledger(request,source_entry,output):
    root=Path(request['privateRoot']).resolve();output=private_path(output,root)
    if output.exists():raise PreopenError('REFUSE_OVERWRITE_STATE_LEDGER')
    source=json.loads(verify_entry(source_entry,root).read_text())
    if source['sourcesHash']!=digest(request['sources']):raise PreopenError('STATE_SOURCE_STAGE_BINDING')
    db=verify_entry(source['database'],root)
    contract=request['stateGeneratorContract']
    files,Engine,Bar,parse,norm80,norm120=pinned_upstream(contract,root)
    profile=json.loads(files['profile.json'].read_text())
    artifact=digest({n:contract['files'][n]['sha256'] for n in ('api.py','exact.py','kernel.py','normalize80.py','normalize120.py')})
    lineage={'kind':'DETERMINISTIC_FROZEN_RULES','requiresFit':False,'profileSha256':contract['files']['profile.json']['sha256'],
             'contractSha256':contract['files']['RC2_CONTRACT.txt']['sha256'],'artifactSha256':artifact}
    calendar=request['exchangeSessions'];splits=json.loads(verify_entry(request['admission'],root).read_text())['exactSplits']
    sessions=sorted({calendar[calendar.index(d)-1] for dates in splits.values() for d in dates})
    store=CompactNativeStore(db.parent,private_root=root,request=request)
    counts=Counter();checks=0
    with output.open('x',encoding='utf-8') as stream:
        stream.write('{"schema":"ARK_PREOPEN_PRIOR_STATE_LEDGER_V1","rows":[');sep=''
        for session in sessions:
            prev=calendar[calendar.index(session)-1]
            for code, in store.connection.execute("SELECT symbol FROM compact_intraday WHERE dataset='MINUTE' AND session=? ORDER BY symbol",(session,)):
                row={'session':session,'symbol':code,'formalObserved':False,'primary':None,'upstreamLineage':lineage}
                current=list(store.records('MINUTE',session=session,code=code))
                before=list(store.records('MINUTE',session=prev,code=code))
                segment=terminal_segment(current,session)
                if not before:
                    reason='NOT_AVAILABLE_IN_SOURCE'
                elif not store.minute_complete(session,code) or not store.minute_complete(prev,code):
                    reason='PIT_OR_BASIS_UNVERIFIED'
                elif not segment:
                    reason='FORMAL_STATE_NOT_OBSERVED_AT_CONTINUOUS_CLOSE'
                else:
                    daily=list(store.records('DAILY',session=session,code=code))+list(store.records('DAILY',session=prev,code=code))
                    if len(daily)!=2 or any(r.get('AdjFactor') in (None,'','None','null') or Decimal(r['AdjFactor'])!=1 for r in daily):
                        reason='PIT_OR_BASIS_UNVERIFIED'
                    else:
                        try:
                            a=normalized_coordinates(before,segment,80);b=normalized_coordinates(before,segment,120)
                        except PreopenError as exc:
                            if str(exc)!='STATE_SCALE_INSUFFICIENT_LOOKBACK':raise
                            row['missingReason']='INSUFFICIENT_LOOKBACK'
                            counts['INSUFFICIENT_LOOKBACK']+=1
                            stream.write(sep+json.dumps(row,ensure_ascii=False,allow_nan=False,separators=(',',':')));sep=','
                            continue
                        for k in ('U','P_ref','previous_return_pairs_N','coordinates'):
                            if a[k]!=b[k]:raise PreopenError('STATE_NORMALIZATION_PRECISION_MISMATCH:'+k)
                        if checks<64:
                            official80=norm80.generate([{**r,'_source':r['_sourceHash']+':'+str(r['_ordinal'])} for r in before],segment)
                            official120=norm120.regenerate([{**r,'_source':r['_sourceHash']+':'+str(r['_ordinal'])} for r in before],segment)
                            for k in ('U','P_ref','previous_return_pairs_N','coordinates','flags'):
                                if a[k]!=official80[k] or b[k]!=official120[k]:raise PreopenError('STATE_MEMOIZED_NORMALIZER_CHANGED:'+k)
                            checks+=1
                        engine=Engine(profile);result=None
                        for raw,coord in zip(segment,a['coordinates']):
                            t=int(raw['Time'][:2])*60+int(raw['Time'][3:5])+1
                            bar=Bar(t=t,o=parse(coord['O']),h=parse(coord['H']),l=parse(coord['L']),c=parse(coord['C']),
                                    known_at=t,source='JQUANTS_RAW_CONTINUOUS_1M',auction=False)
                            result=engine._step(t,bar)
                        if result['current_semantics_observed']:
                            row.update(formalObserved=True,primary=result['primary'],
                                observedAt=session+'T'+cash_clock(session)['continuous_close']+':00+09:00',
                                knownAt=max(store.available_at(r,'MINUTE') for r in (current[-1],before[-1])),
                                sourceHashes=sorted({r['_sourceHash'] for r in before+current}),numericPrecision='DECIMAL80_Q1E-24_WITH_DECIMAL120_MATCH',
                                formalBasis=result['basis'],U=a['U'],referencePrice=a['P_ref'])
                            reason=None
                        else:reason='FORMAL_STATE_NOT_OBSERVED'
                if reason:row['missingReason']=reason
                counts[row.get('primary') or reason]+=1
                stream.write(sep+json.dumps(row,ensure_ascii=False,allow_nan=False,separators=(',',':')));sep=','
            print(json.dumps({'stateSessionCompleted':session,'rowsSoFar':sum(counts.values())}),flush=True)
        stream.write(']}\n')
    store.close();h,n=sha_file(output)
    entry={'path':str(output),'sha256':h,'bytes':n}
    joined={'reviewed':True,'evidenceReference':'Pinned Frozen RC2 M0 and semantic contract; formal D-1 continuous-close only',
        'cutoffPolicy':'D_MINUS_1_CONTINUOUS_CLOSE_FORMAL_OBSERVED','ledger':entry,**{k:lineage[k] for k in ('profileSha256','contractSha256','artifactSha256')}}
    receipt=write_json(output.with_name(output.stem+'_RECEIPT.json'),{'schema':'ARK_CAUSAL_FROZEN_STATE_GENERATION_V1',
        'ledger':entry,'previousStateContract':joined,'rowN':sum(counts.values()),'statesAndMissingReasons':dict(counts),
        'official80AndIndependent120NormalizersCheckedSecurityDays':checks,'retuned':False,'upstreamFits':0,
        'sourceStageReceiptSha256':source_entry['sha256'],'sourcesHash':digest(request['sources']),'createdAt':utc_now(),**SAFE_FLAGS})
    return receipt

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--request',required=True);p.add_argument('--source-receipt-entry',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();request=json.loads(Path(a.request).read_text());source=json.loads(Path(a.source_receipt_entry).read_text())
    print(json.dumps(generate_state_ledger(request,source,Path(a.output))))

if __name__=='__main__':main()
