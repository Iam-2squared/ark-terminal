"""Descriptive analysis of saved Phase A outcomes; never calls a policy engine."""
from __future__ import annotations
import collections
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
from scripts.phase57_post_prr_a_plus import BASE, OUT, D, S, read, rows, sha, write, write_rows

Z=Decimal(0)
def key(r):return r['world'],r['arm'],r['entryId']
def money(x):return D(x) if x is not None else None
def labels(r):
    v=r['futureUpsidePctEvaluatorOnly']
    if v is None:return 'UNKNOWN'
    v=D(v)
    return '<1' if v<1 else '[1,3)' if v<3 else '[3,5)' if v<5 else '[5,10)' if v<10 else '[10,inf)'
def qtile(values,p):
    if not values:return None
    a=sorted(values);h=Decimal(len(a)-1)*Decimal(str(p));lo=int(h);w=h-lo
    return S(a[lo]*(1-w)+a[min(lo+1,len(a)-1)]*w)
def sign(v):return 'UNKNOWN' if v is None else 'NEG' if v<0 else 'POS' if v>0 else 'ZERO'

def build():
    a=rows('ACCOUNTING_RECONCILIATION_ROWS.jsonl.gz')
    m={key(r):r for r in rows('COMPARISON_MASK_ROWS_INTENT_V2.jsonl.gz')}
    assert len(a)==len(m)==1725
    out=[]
    for r in a:
        t=dict(r);v=m[key(r)]
        assert t['session']==v['session'] and t['quantity']==v['quantity'] and t['entryPrice']==v['entryPrice']
        intent=t['ccmgFirstIntentMinute'];control=t['controlDecisionMinute']
        cls=('NO_CCMG_INTENT_IN_RECORDED_SCOPE' if intent is None else
             'CCMG_FIRST_WHILE_CONTROL_ACTIVE' if intent<control else
             'CONTROL_INTENT_ALREADY_ISSUED' if intent>control else 'SAME_TIME_INTENT_UNRESOLVED')
        cost=D(r['entryCostJpy']);dp=None
        if r['ccmgExitPrice'] is not None and r['controlExitPrice'] is not None:
            dp=D(r['quantity'])*(D(r['ccmgExitPrice'])-D(r['controlExitPrice']))
            assert dp==D(r['deltaPnlJpy']),key(r)
        dn=None if dp is None else 100*dp/cost
        route_dp=(dp if r['routeDecision']=='DEFENSIVE_ELIGIBLE' else Z) if r['controlExitPrice'] is not None and (dp is not None or r['routeDecision']=='CONTROL_DEFAULT') else None
        # Source-derived equality, not saved A1 mean or its superseded order.
        t.update(intentClass=cls,provisionalEligibility=(cls=='CCMG_FIRST_WHILE_CONTROL_ACTIVE' and v['runtime_feature_asof_valid']),labelKnown=dp is not None,
          deltaNetPp=S(dn),deltaPnlJpy=S(dp),band5=labels(r),
          routeDeltaPnlJpy=S(route_dp),routeDeltaNetPp=S(None if route_dp is None else 100*route_dp/cost),
          guardTracePresent=v['causalGuardTraceAtIntent'],runtimeAsOf=v['runtime_feature_asof_valid'],
          controlOutcomeKnown=v['control_outcome_known'],ccmgOutcomeKnown=v['ccmg_outcome_known'],
          firstIntentKnown=v['has_ccmg_first_intent'],firstIntentToControlWallMinutes=None if intent is None else control-intent)
        out.append(t)
    write_rows('INTENT_UNIVERSE_ROWS.jsonl.gz',out)
    return out

def scope(rows,arm,world):
    return [r for r in rows if r['arm']==arm and (r['world']=='PRIMARY_FUNDED' if world=='PRIMARY_FUNDED' else r['world']=='ALL_100' and (world=='ALL_100' or (r['primary'] if world=='PRIMARY_100' else not r['primary'])))]
def subset(rs,typ):
    return [r for r in rs if typ=='ALL' or typ=='I' and r['firstIntentKnown'] or typ=='E' and r['provisionalEligibility'] or typ=='TIE' and r['intentClass']=='SAME_TIME_INTENT_UNRESOLVED' or typ=='NO_INTENT' and not r['firstIntentKnown']]

def census(allrows):
    t={};unknown=[]
    for arm in ('IM','R1'):
      rs=scope(allrows,arm,'ALL_100');I=[r for r in rs if r['firstIntentKnown']]
      K=[r for r in rs if r['labelKnown']]
      only=[r for r in rs if r['controlOutcomeKnown'] and not r['ccmgOutcomeKnown']]
      missingI=[r for r in I if not r['labelKnown']]
      setonly={r['entryId'] for r in only};setI={r['entryId'] for r in missingI}
      # Exact set differences, no inference from coincident aggregate counts.
      table={'allN':len(rs),'I':len(I),'E_provisional':sum(r['provisionalEligibility'] for r in rs),'K':len(K),'I_intersect_K':sum(r['labelKnown'] for r in I),
        'E_intersect_K':sum(r['labelKnown'] and r['provisionalEligibility'] for r in rs),'controlOnlyN':len(only),'bothUnknownN':sum(not r['controlOutcomeKnown'] and not r['ccmgOutcomeKnown'] for r in rs),
        'I_minus_K_IDs':sorted(setI),'controlOnly_minus_IminusK_IDs':sorted(setonly-setI),'IminusK_minus_controlOnly_IDs':sorted(setI-setonly),
        'intentClassN':dict(collections.Counter(r['intentClass'] for r in rs)),
        'intentByRouteN':{route:{'I':sum(r['firstIntentKnown'] for r in rs if r['routeDecision']==route),'K':sum(r['labelKnown'] for r in rs if r['routeDecision']==route),'all':sum(r['routeDecision']==route for r in rs)} for route in ('DEFENSIVE_ELIGIBLE','CONTROL_DEFAULT')},
        'intentDeltaCrosstab':dict(collections.Counter(('I' if r['firstIntentKnown'] else 'NO_INTENT',sign(money(r['deltaPnlJpy']))) for r in rs)),
        'unknownNoIntentIDs':sorted(r['entryId'] for r in rs if not r['firstIntentKnown'] and not r['labelKnown']),
        'unknownStatus':dict(collections.Counter((r['fillStatus'],r['terminalReason'],r['routeDecision'],r['intentClass']) for r in missingI))}
      # JSON object keys must be strings.
      table['intentDeltaCrosstab']={str(k):v for k,v in table['intentDeltaCrosstab'].items()}
      table['unknownStatus']={str(k):v for k,v in table['unknownStatus'].items()}
      assert len(setI)==80 and not(setonly^setI)
      t[arm]=table
      unknown += [{'arm':arm,'entryId':r['entryId'],'session':r['session'],'symbol':r['symbol'],'route':r['routeDecision'],'intentMinute':r['ccmgFirstIntentMinute'],'controlDecisionMinute':r['controlDecisionMinute'],'fillStatus':r['fillStatus'],'terminalReason':r['terminalReason'],'intentClass':r['intentClass'],'cause':'MISSING_EXACT_NEXT_SCHEDULED_OPEN_REFERENCE','causeKnownAt':'AFTER_INTENT','canMeasureAllowOutcome':False} for r in missingI]
    write('INTENT_CENSUS.json',{'schema':'phase57-a-plus-intent-census-v1','arms':t,'countedWorld':'ALL_100','E':'provisional: CCMG first < control decision and guard as-of flag; branch equivalence remains partial','traceScope':'stops at first candidate or R50 ceiling; no R50-first observed by construction'})
    write_rows('UNKNOWN_FIRST_INTENT_ROWS.jsonl.gz',unknown)
    write('MISSINGNESS_AUDIT.json',{'schema':'phase57-a-plus-missingness-v1','sourceCode':'scripts/phase57_ccmg_guard.py::run_entry; scripts/phase57_exit_execution_contract_v1.py::ordinary_execution_reference','80PerArm':'all have first intent, missing exact scheduled next OPEN; queuedIntent false, no retry/ffill; later reference availability not known at intent','missingAtIntent':False,'unknownRowsFile':'UNKNOWN_FIRST_INTENT_ROWS.jsonl.gz','noTradeOrHaltEstablished':False,'allowOutcome':'ALLOW_OUTCOME_UNMEASURABLE','bothUnknownNoIntent':{'IM':t['IM']['unknownNoIntentIDs'],'R1':t['R1']['unknownNoIntentIDs']},'noImputation':True})
    write('INTENT_ORDER_AND_BRANCH_EQUIVALENCE.json',{'schema':'phase57-a-plus-branch-v1','intentCounts':{arm:t[arm]['intentClassN'] for arm in t},'clock':'minutes after midnight, 925=15:25 decision endpoint; terminal auction reference 930; lunch excluded from active elapsed, not wall','trace':'readiness trace grid <= R50 decisionNow; breaks on first SELL_INTENT; no R50-after intent trace witness; no-intent is within this recorded scope only','simultaneous':'tie event order/pending ownership unresolved; excluded from provisional E','R50First':'0 by observation geometry, no predictive advantage inference','pending':'execution contract queuedIntent=false for missing exact OPEN; historical R50 model pending state per-row not fully witnessed','ALLOW':'saved CCMG first-sale contract statically supported when exact reference exists; 80+80 missing candidate price, no new fallback','ABSTAIN':'R50 ledger computed separately, guard reads ceiling/control; one-shot handoff concept statically plausible; row-level hidden R50 state equivalence not fully proved','status':'STATIC_CONTRACT_SUPPORTED_ROW_WITNESS_PARTIAL_NOT_EXPERIMENT_READY'})

def summarize(rs,field='deltaPnlJpy'):
    known=[r for r in rs if r[field] is not None]
    values=[D(r[field]) for r in known]
    netfield='routeDeltaNetPp' if field=='routeDeltaPnlJpy' else 'deltaNetPp'
    net=[D(r[netfield]) for r in known if r[netfield] is not None]
    return {'N_total':len(rs),'N_known':len(known),'N_unknown':len(rs)-len(known),'sessions_total':len({r['session'] for r in rs}),'sessions_known':len({r['session'] for r in known}),'symbols':len({r['symbol'] for r in rs}),
      'negativeN':sum(x<0 for x in values),'zeroN':sum(x==0 for x in values),'positiveN':sum(x>0 for x in values),'sumDeltaJpy':S(sum(values,Z)) if known else None,'meanDeltaJpy':S(sum(values,Z)/len(values)) if known else None,'meanDeltaNetPp':S(sum(net,Z)/len(net)) if net else None,
      'medianDeltaJpy':qtile(values,.5),'p05DeltaJpy':qtile(values,.05),'p25DeltaJpy':qtile(values,.25),'p75DeltaJpy':qtile(values,.75),'p95DeltaJpy':qtile(values,.95)}

def groups(allrows):
  output={};zero={};decomp={};matched={}
  for arm in ('IM','R1'):
    world={w:scope(allrows,arm,w) for w in ('ALL_100','PRIMARY_100','PRIMARY_FUNDED','PRIMARY_OUTSIDE_100')}
    for w,rs in world.items():
      for route in ('ALL','DEFENSIVE_ELIGIBLE','CONTROL_DEFAULT'):
       for typ in ('ALL','I','E','TIE','NO_INTENT'):
        z=[r for r in subset(rs,typ) if route=='ALL' or r['routeDecision']==route]
        for band in ('ALL','<1','[1,3)','[3,5)','[5,10)','[10,inf)','UNKNOWN'):
         sample=[r for r in z if band=='ALL' or r['band5']==band]
         if not sample and band=='ALL' and typ=='ALL':raise AssertionError('EMPTY_WORLD')
         output['|'.join([arm,w,route,typ,band])]={'component':summarize(sample),'frozenRouteAvailable':summarize(sample,'routeDeltaPnlJpy'),'frozenRouteOnPairedMask':summarize([r for r in sample if r['labelKnown']],'routeDeltaPnlJpy')}
    # Common-mask quantity decomposition and unmatched residuals.
    p100={r['entryId']:r for r in world['PRIMARY_100']};pf={r['entryId']:r for r in world['PRIMARY_FUNDED']}
    assert set(p100)==set(pf)
    for typ in ('component','route'):
      field='deltaPnlJpy' if typ=='component' else 'routeDeltaPnlJpy'
      common=[(p100[k],pf[k]) for k in sorted(p100) if p100[k][field] is not None and pf[k][field] is not None]
      errors=[];qty=Z
      for x,y in common:
        assert x['entryPrice']==y['entryPrice'] and x['ccmgExitPrice']==y['ccmgExitPrice'] and x['controlExitPrice']==y['controlExitPrice'] and x['routeDecision']==y['routeDecision']
        d=D(x[field])/100
        qty+=(D(y['quantity'])-100)*d
        if D(y[field])!=D(x[field])+D(y['quantity']-100)*d:errors.append(x['entryId'])
      assert not errors
      allknown={r['entryId'] for r in world['ALL_100'] if r[field] is not None}
      commonids={x['entryId'] for x,y in common}
      outside=sum((D(r[field]) for r in world['PRIMARY_OUTSIDE_100'] if r[field] is not None),Z)
      ps=sum((D(x[field]) for x,y in common),Z);funded=sum((D(y[field]) for x,y in common),Z)
      total=sum((D(r[field]) for r in world['ALL_100'] if r[field] is not None),Z)
      decomp[f'{arm}|{typ}']={'commonPrimaryN':len(common),'primaryTotalN':len(p100),'primaryFundedDeltaJpy':S(funded),'primary100DeltaJpy':S(ps),'quantityTermJpy':S(qty),'identityResidualJpy':S(funded-ps-qty),'outside100KnownContributionJpy':S(outside),'all100KnownContributionJpy':S(total),'all100_minus_primary100_minus_outsideResidualJpy':S(total-ps-outside),'unmatchedPrimaryIds':sorted(set(p100)-commonids),'pricePathMismatchIds':[]}
      assert funded-ps-qty==0 and total-ps-outside==0
  # Exact zero in R1 5-10: signed cancellation, not null defaults.
  r=[r for r in scope(allrows,'R1','ALL_100') if r['band5']=='[5,10)']
  ids={sg:sorted(x['entryId'] for x in r if sign(money(x['deltaPnlJpy']))==sg) for sg in ('POS','NEG','ZERO','UNKNOWN')}
  zero={'band':'[5,10)','arm':'R1','counts':{k:len(v) for k,v in ids.items()},'sumsJpy':{k:S(sum((D(x['deltaPnlJpy']) for x in r if x['entryId'] in set(ids[k]) and x['deltaPnlJpy'] is not None),Z)) for k in ids},'idSetChecksums':{k:hashlib.sha256(('\n'.join(v)+'\n').encode()).hexdigest() for k,v in ids.items()}}
  write('FINE_BUCKET_ROUTE_RESULTS.json',{'schema':'phase57-a-plus-groups-v1','rows':output,'bandSource':'futureUpsidePctEvaluatorOnly; evaluator-only, exclusive','E':'provisional; all underlying rows saved','units':{'sumDeltaJpy':'JPY','meanDeltaNetPp':'percentage points'},'sourceRowsSha256':sha(OUT/'INTENT_UNIVERSE_ROWS.jsonl.gz')})
  write('ACCOUNTING_AND_PRIMARY_DECOMPOSITION.json',{'schema':'phase57-a-plus-world-decomposition-v1','byArmComparison':decomp,'r1FiveToTenZeroAudit':zero,'formula':'funded=primary100+Σ(q−100)*(exitC−exitR); primary and outside common mask separately','sameMaskAndPriceVerified':True,'portfolioClaim':False})
  return output

def tail_one(rs,field):
  known=[r for r in rs if r[field] is not None]
  totalPos=sum((max(D(r[field]),Z) for r in known),Z);totalNeg=sum((max(-D(r[field]),Z) for r in known),Z)
  sides={}
  for s,tot in [('gain',totalPos),('loss',totalNeg)]:
    vals=[(max(D(r[field]) if s=='gain' else -D(r[field]),Z),r) for r in known]
    vals.sort(key=lambda x:(-x[0],x[1]['session'],x[1]['arm'],x[1]['entryId']))
    positive=[(v,r) for v,r in vals if v>0]
    cumul=Z;curve=[]
    for v,r in positive:
      cumul+=v;curve.append({'entryId':r['entryId'],'session':r['session'],'symbol':r['symbol'],'contributionJpy':S(v),'cumulativeJpy':S(cumul),'fraction':S(cumul/tot) if tot else None})
    sides[s]={'grossJpy':S(tot),'contributors':len(positive),'topShares':{str(n):S(sum((v for v,r in positive[:n]),Z)/tot) if tot else None for n in (1,3,5,10)},'minimumTo50Pct':next((i+1 for i,x in enumerate(curve) if D(x['fraction'])>=Decimal('.5')),None),'status':'DEFINED' if tot else ('NOT_DEFINED_NO_GAIN' if s=='gain' else 'NOT_DEFINED_NO_LOSS'),'curve':curve}
  return {'N_total':len(rs),'N_known':len(known),'N_unknown':len(rs)-len(known),'grossGainJpy':S(totalPos),'grossLossJpy':S(totalNeg),'netDeltaJpy':S(totalPos-totalNeg),'sides':sides}

def tail_loo(allrows):
  sessions=sorted({r['session'] for r in allrows if r['world']=='ALL_100'})
  assert len(sessions)==24
  result={};loo={};contributions=[]
  for arm in ('IM','R1'):
    for world in ('ALL_100','PRIMARY_100','PRIMARY_FUNDED','PRIMARY_OUTSIDE_100'):
      for typ in ('ALL','I','E'):
       rs=subset(scope(allrows,arm,world),typ)
       for comp,field in (('component','deltaPnlJpy'),('frozenRoute','routeDeltaPnlJpy')):
        name='|'.join([arm,world,typ,comp]);result[name]=tail_one(rs,field)
        baseline=summarize(rs,field)
        rowsout=[]
        for axis,values in [('session',sessions),('symbol',sorted({r['symbol'] for r in rs}))]:
         for val in values:
          remain=[r for r in rs if r[axis]!=val]
          z=summarize(remain,field)
          v=D(z['sumDeltaJpy']) if z['sumDeltaJpy'] is not None else None
          b=D(baseline['sumDeltaJpy']) if baseline['sumDeltaJpy'] is not None else None
          rowsout.append({'axis':axis,'omitted':val,'remaining':z,'changeFromBaselineJpy':S(v-b) if v is not None and b is not None else None,'signReversed':v*b<0 if v is not None and b is not None else None})
        loo[name]=rowsout
        for axis in ('session','symbol'):
         for val in sorted({r[axis] for r in rs}):
          sub=[r for r in rs if r[axis]==val]
          gain=sum((max(D(r[field]),Z) for r in sub if r[field] is not None),Z)
          loss=sum((max(-D(r[field]),Z) for r in sub if r[field] is not None),Z)
          contributions.append({'name':name,'axis':axis,'value':val,'N_total':len(sub),'N_unknown':sum(r[field] is None for r in sub),'grossGainJpy':S(gain),'grossLossJpy':S(loss),'netDeltaJpy':S(gain-loss)})
  write('TAIL_AND_LOO.json',{'schema':'phase57-a-plus-tail-loo-v1','tail':result,'allLeaveOneOut':loo,'sessionsFixed':sessions,'method':'signed gross separately; all sessions and symbols omitted symmetrically; known subset, unknown retained'})
  write_rows('GROUP_CONTRIBUTIONS.jsonl.gz',contributions)

def rank(allrows):
  out={};rowsout=[]
  for arm in ('IM','R1'):
   for typ in ('ALL','I','E'):
    rs=subset(scope(allrows,arm,'ALL_100'),typ)
    for route in ('ALL','DEFENSIVE_ELIGIBLE','CONTROL_DEFAULT'):
     g=[r for r in rs if route=='ALL' or r['routeDecision']==route]
     blocks={}
     for head,col in [('5','score5'),('10','score10')]:
      for dec in range(1,11):
       z=[r for r in g if r['rank'+head+'Decile']==dec]
       blocks[f'{head}|{dec}']=summarize(z)
      known=[r for r in g if r['labelKnown'] and r[col] is not None]
      corr=spearmanr([r[col] for r in known],[float(D(r['deltaNetPp'])) for r in known]).statistic if len(known)>=2 else float('nan')
      out['|'.join([arm,typ,route,head])]={'N_total':len(g),'N_known':len(known),'N_unknown':len(g)-len(known),'spearmanScoreVsDeltaNetPp':None if math.isnan(corr) else corr,'deciles':{k:v for k,v in blocks.items() if k.startswith(head+'|')},'folds':{str(f):summarize([r for r in g if r['fold']==f]) for f in sorted({r['fold'] for r in g})},'missingByDecile':{str(d):{'N':sum(r['rank'+head+'Decile']==d for r in g),'unknown':sum(r['rank'+head+'Decile']==d and not r['labelKnown'] for r in g)} for d in range(1,11)}}
  write('RANK_DELTA_ANATOMY.json',{'schema':'phase57-a-plus-rank-v1','armsScopesRoutesHeads':out,'score':'frozen canonical OOF, no refit','interpretation':'conditional descriptive association; intent and observed outcome are different selection mechanisms'})

def main():
 assert sha(OUT/'A_PLUS_PRECOMMIT.json')==(OUT/'A_PLUS_PRECOMMIT.sha256').read_text().split()[0]
 assert sha(OUT/'ANALYSIS_SPEC.json')==(OUT/'ANALYSIS_SPEC.sha256').read_text().split()[0]
 a=build();census(a);groups(a);tail_loo(a);rank(a)
 print('ANALYSIS',len(a),sha(OUT/'INTENT_UNIVERSE_ROWS.jsonl.gz'))
if __name__=='__main__':main()
