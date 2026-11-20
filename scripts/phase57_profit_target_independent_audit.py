"""Independent decision and Decimal accounting path for the saved 14 arms.

Source projection is shared only to enforce the frozen allowlist. All target
clocks, references, quantities and JPY/pp are calculated without importing
the main market_row, pnl or summary implementation.
"""
import collections
import gzip
import json
import math
from decimal import Decimal

from scripts import phase57_profit_target_diagnostic as main
from scripts.phase57_profit_target_precommit import OUT, ARM, TARGETS, canonical, digest, jst, check


def admitted(arm,entry_id,target,universe):
    if target not in TARGETS or arm not in ARM or entry_id not in universe[arm]:
        raise ValueError('AUDIT_SCOPE_REJECTED')


def independent(entry,control,raw,target):
    day=entry['session'];start=entry['entryMinute'];e=Decimal(str(entry['entryPrice']))
    grid=list(range(540,690))+list(range(750,925))
    valid={}
    for m in grid:
        if m<start or m not in raw:continue
        b=raw[m]
        if (len(b)==7 and b[0]==m and all(isinstance(v,(int,float)) and
             not isinstance(v,bool) and math.isfinite(v) for v in b) and
             b[1]>0 and b[3]>0 and b[3]<=min(b[1],b[4])<=max(b[1],b[4])<=b[2] and
             b[5]>=0 and b[6]>=0):
            valid[m]=b
    hit=None
    for m in grid:
        if m not in valid or m<start:continue
        if (Decimal(str(valid[m][4]))/e-1)*100 >= Decimal(target):
            hit=m+1;break
    decision=control['decisionNow']
    if hit is not None and hit<decision:
        schedule=[m for m in grid if m>=hit]
        ref=schedule[0] if schedule else None
        chosen=valid.get(ref)
        fill=chosen[1] if chosen is not None else None
        status='TARGET' if chosen is not None else 'TARGET_FIRST_REFERENCE_UNRESOLVED'
    else:
        ref=None;status='R50';fill=control['exitPrice']
    return {'firstObservedTargetNow':hit,'prior':hit is not None and hit<decision,
            'tie':hit==decision,'choice':status,'targetRef':ref,
            'fill':fill,'r50':control['exitPrice'],
            'wholeExpectedBars':sum(m>=start for m in grid),
            'wholeObservedBars':len(valid)}


def calc(fill,quantity,cost):
    if fill is None:return None
    p=Decimal(str(fill));b=Decimal(str(cost));q=Decimal(quantity)
    return q*p - b - b*Decimal('0.0005')


def self_test():
    day='2025-07-22';e={'session':day,'entryMinute':540,'entryPrice':100.0}
    c={'decisionNow':545,'exitPrice':101.0}
    b=lambda m,h,z:[m,100.,h,99.,z,10.,1000.]
    path={540:b(540,105,102),541:b(541,104,103),542:b(542,103,100)}
    r=independent(e,c,path,3)
    check(r['choice']=='TARGET' and r['targetRef']==542 and r['fill']==100.,'AUDIT_SYNTH_TARGET')
    check(independent(e,c,{540:path[540],541:path[541]},3)['choice']==
          'TARGET_FIRST_REFERENCE_UNRESOLVED','AUDIT_SYNTH_MISSING')
    check(independent(e,{**c,'decisionNow':541},path,2)['tie'],'AUDIT_SYNTH_TIE')
    check(independent(e,c,{540:path[540]},4)['choice']=='R50','AUDIT_HIGH_ONLY')
    check(calc(103,100,'10000')-calc(101,100,'10000')==Decimal(200),'AUDIT_COST')
    for bad in (11,-1):
        try:admitted('IM','X',bad,{'IM':{'X'}})
        except ValueError:pass
        else:raise AssertionError('TARGET_SCOPE_CANARY')
    try:admitted('IM','PROTECTED_ID',3,{'IM':{'X'}})
    except ValueError:pass
    else:raise AssertionError('PROTECTED_ID_CANARY')
    print('Independent synthetic clocks, missing, tie, high-only, Decimal, scope PASS')


def audit():
    check(not (OUT/'AUDIT_STARTED.json').exists(),'AUDIT_ALREADY_ATTEMPTED')
    saved=main.read_gz(OUT/'FIXED_TARGET_OUTCOME_ROWS.jsonl.gz')
    check(len(saved)==11298,'SAVED_ROW_SCOPE')
    pre,entries,ledgers,controls,paths,_=main.load_verified()
    (OUT/'AUDIT_STARTED.json').write_bytes(canonical({'atJst':jst(),
        'samePolicyArmIdentities':14,'independentRecalculationsPlanned':14,
        'savedRowsSha256':digest(OUT/'FIXED_TARGET_OUTCOME_ROWS.jsonl.gz')}))
    mismatches=[];totals=collections.defaultdict(lambda:collections.defaultdict(Decimal))
    coverage=collections.Counter()
    for old in saved:
        a=old['arm'];eid=old['entryId'];x=old['targetPct']
        admitted(a,eid,x,entries)
        e=entries[a][eid];c=controls[a][eid]
        v=independent(e,c,paths[e['opportunityId']],x)
        for field,computed in (('firstObservedClosedTargetNow',v['firstObservedTargetNow']),
                  ('firstClosedTargetBeforeR50Intent',v['prior']),
                  ('sameTimeControlDelegation',v['tie']),('choice',v['choice']),
                  ('targetReferenceMinute',v['targetRef']),('candidateFillPrice',v['fill']),
                  ('r50FillPrice',v['r50']),('wholeExpectedBars',v['wholeExpectedBars']),
                  ('wholeObservedBars',v['wholeObservedBars'])):
            if old[field]!=computed:mismatches.append([a,eid,x,field])
        for key,q,b in [('100',100,e['entryCostJpy']),
                        ('actual',ledgers[a]['funded'][eid]['quantity'] if
                          eid in ledgers[a]['funded'] else None,
                          ledgers[a]['funded'][eid]['notionalJpy'] if
                          eid in ledgers[a]['funded'] else None)]:
            if q is None:continue
            candidate=calc(v['fill'],q,b);baseline=calc(v['r50'],q,b)
            delta=candidate-baseline if candidate is not None and baseline is not None else None
            for field,computed in (('candidatePnlJpy',candidate),('r50PnlJpy',baseline),
                                   ('deltaJpy',delta)):
                actual=old[key][field]
                if ((actual is None)!=(computed is None) or
                    (actual is not None and
                     abs(Decimal(actual)-computed)>Decimal('0.000001'))):
                    mismatches.append([a,eid,x,key+'.'+field])
            if key=='actual' and delta is not None:
                sums=totals[a,x]
                sums['deltaJpy']+=delta;sums['candidateJpy']+=candidate;sums['r50Jpy']+=baseline
                sums['pairedN']+=1
        coverage[a,x]+=1
    summary=json.loads((OUT/'FIXED_TARGET_RESULTS.json').read_text())
    for (a,x),s in totals.items():
        known=summary[f'{a}:{x}']['R50_FUNDED_ACTUAL']['targetSpecific']
        for k,v in [('deltaJpy','deltaJpySameMask'),('candidateJpy','candidatePnlJpySameMask'),
                    ('r50Jpy','r50PnlJpySameMask'),('pairedN','pairedKnownN')]:
            if abs(s[k]-Decimal(str(known[v])))>Decimal('0.000001'):
                mismatches.append([a,x,'FUNDED_SUMMARY',k])
    status='PASS_SAVED_ROWS_INDEPENDENT_RECALCULATION' if not mismatches else 'FAIL_ROW_OR_SUMMARY_MISMATCH'
    result={'status':status,'atJst':jst(),'sourcePriceHash':pre['sourceManifestSha256'],
            'savedRowsSha256':digest(OUT/'FIXED_TARGET_OUTCOME_ROWS.jsonl.gz'),
            'identicalPolicyArmRecalculations':14,'newPolicyFamiliesExplored':0,
            'rowsCompared':len(saved),'mismatchN':len(mismatches),'firstMismatches':mismatches[:50],
            'scopeCount':{f'{a}:{x}':n for (a,x),n in coverage.items()},
            'sharedSourceProjection':'allowlisted_raw_paths; independent policy clock, reference and Decimal accounting',
            'originalRunStatus':'INVALID_RUN_POSTPROCESS_EXCEPTION',
            'independentMarketValidation':False,'newProviderRequests':0,
            'protectedOpened':0,'newFits':0,'orders':0}
    (OUT/'INDEPENDENT_AUDIT.json').write_bytes(canonical(result))
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    import sys
    check(len(sys.argv)==2 and sys.argv[1] in ('--self-test','--audit'),'MODE')
    self_test() if sys.argv[1]=='--self-test' else audit()
