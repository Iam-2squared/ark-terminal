"""Independent raw-price rebuild of Phase A; no reuse of analysis functions."""
from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'docs/evidence/phase57-post-prr-phase-a'
CCMG=ROOT/'docs/evidence/phase57-checkpoint-certified-guard-exit'
PRR=ROOT/'docs/evidence/phase57-prr-numerical-recovery'
FEE=Decimal('0.0005')


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text())
def rowfile(path):
    with gzip.open(path,'rt') as f:return [json.loads(line) for line in f]
def dec(x):return Decimal(str(x))
def verify(ok,msg):
    if not ok:raise AssertionError(msg)


def main():
    pre=load(DEST/'PHASE_A_PRECOMMIT.json')
    verify(digest(DEST/'PHASE_A_PRECOMMIT.json')==(DEST/'PHASE_A_PRECOMMIT.sha256').read_text().split()[0],'PRECOMMIT_SHA')
    spec=load(DEST/'A1_ANALYSIS_SPEC.json')
    verify(digest(DEST/'A1_ANALYSIS_SPEC.json')==(DEST/'A1_ANALYSIS_SPEC.sha256').read_text().split()[0],'A1_SPEC_SHA')
    verify(spec['a0Sha256']==digest(DEST/'A0_CENSUS.json') and
           spec['a0FreezeSha256']==digest(DEST/'A0_FREEZE.json'),'A0_FREEZE')
    for pin in pre['sourcePins'].values():
        verify(digest(ROOT/pin['path'])==pin['sha256'],'SOURCE_PIN:'+pin['path'])
    for folder,member in ((PRR,'fileSha256'),(CCMG,'filesSha256')):
        for name,expected in load(folder/'MANIFEST.json')[member].items():
            verify(digest(folder/name)==expected,'MANIFEST_DRIFT:'+name)
    original={(r['arm'],r['entryId']):r for r in rowfile(CCMG/'LAYER_A_ENTRY_ROWS.jsonl.gz')}
    source_summary={(r['arm'],r['entryId']):r for r in rowfile(CCMG/'CHECKPOINT_ENTRY_SUMMARY.jsonl.gz')}
    route={(r['arm'],r['entryId']):r for r in rowfile(PRR/'ROUTE_DECISIONS.jsonl.gz')}
    mask={(r['world'],r['arm'],r['entryId']):r for r in rowfile(DEST/'COMPARISON_MASK_ROWS.jsonl.gz')}
    reconciled={(r['world'],r['arm'],r['entryId']):r for r in rowfile(DEST/'ACCOUNTING_RECONCILIATION_ROWS.jsonl.gz')}
    paired={(r['world'],r['arm'],r['entryId']):r for r in rowfile(DEST/'A1_PAIRED_ROWS.jsonl.gz')}
    result=load(DEST/'A1_RESULTS.json');a0=load(DEST/'A0_CENSUS.json')
    verify(len(original)==1614 and len(source_summary)==1614 and len(route)==1614,'SOURCE_CENSUS')
    verify(len(mask)==len(reconciled)==1725 and len(paired)==1525,'AUDIT_ROW_CENSUS')
    verify(digest(DEST/'ACCOUNTING_RECONCILIATION_ROWS.jsonl.gz')==
           load(DEST/'ACCOUNTING_RECONCILIATION_RECEIPT.json')['rowsSha256'],'ACCOUNTING_RECEIPT_ROWS')
    verify(digest(DEST/'COMPARISON_MASK_ROWS.jsonl.gz')==a0['maskRowsSha256'],'A0_MASK_ROWS')
    verify(digest(DEST/'A1_PAIRED_ROWS.jsonl.gz')==result['pairedRowsSha256'],'A1_PAIRED_ROWS')
    verify(result['specSha256']==digest(DEST/'A1_ANALYSIS_SPEC.json'),'A1_RESULT_SPEC')
    audited=0
    for key,rr in reconciled.items():
        world,arm,eid=key
        raw=original[(arm,eid)]
        q=100 if world=='ALL_100' else raw['quantity']
        verify(world=='ALL_100' or raw['primary'],'FUNDED_ONLY')
        cost=dec(raw['entryPrice'])*q
        verify(dec(rr['entryCostJpy'])==cost and rr['quantity']==q,'ENTRY_COST')
        cx=raw['controlExitPrice'];mx=raw['candidateExitPrice']
        calc_c=None if cx is None else dec(cx)*q-cost*(1+FEE)
        calc_m=None if mx is None else dec(mx)*q-cost*(1+FEE)
        for actual,saved,label in ((calc_c,rr['normalizedControlPnlJpy'],'CONTROL'),
                                    (calc_m,rr['normalizedCcmgPnlJpy'],'CCMG')):
            verify((actual is None and saved is None) or
                   (actual is not None and dec(saved)==actual),'R34_'+label+':'+str(key))
        flags=mask[key]
        verify(flags['control_outcome_known']==(calc_c is not None) and
               flags['ccmg_outcome_known']==(calc_m is not None) and
               flags['paired_outcome_known']==(calc_c is not None and calc_m is not None),'MASK:'+str(key))
        verify(flags['session']==raw['session'] and flags['entryMinute']==raw['entryMinute'] and
               flags['symbol']==eid.split('|')[1] and flags['quantity']==q,'JOIN_FIELDS')
        summary=source_summary[(arm,eid)]
        control_intent=summary['controlNow'] if summary['controlExitKind']=='MODEL_EXIT' else None
        ccmg_intent=summary['firstSellIntent']
        order='UNKNOWN' if control_intent is None or ccmg_intent is None else \
              'CCMG_FIRST' if ccmg_intent<control_intent else \
              'R50_FIRST' if control_intent<ccmg_intent else 'SAME_MINUTE'
        verify(flags['intentOrder']==order and
               flags['control_intent_time_known']==(control_intent is not None) and
               flags['ccmg_first_intent_time_known']==(ccmg_intent is not None),'INTENT_MEANING')
        if calc_c is None or calc_m is None:
            verify(key not in paired and rr['deltaPnlJpy'] is None,'NULL_NOT_IMPUTED')
        else:
            verify(key in paired,'MISSING_PAIRED')
            observed=paired[key]
            verify(dec(observed['deltaPnlJpy'])==calc_m-calc_c and
                   dec(observed['deltaNetPp'])==100*(calc_m-calc_c)/cost and
                   dec(observed['controlNetPct'])==100*calc_c/cost and
                   dec(observed['ccmgNetPct'])==100*calc_m/cost,'PAIRED_NET_AND_YEN')
            selected=calc_m if route[(arm,eid)]['routeDecision']=='DEFENSIVE_ELIGIBLE' else calc_c
            verify(dec(observed['routedDeltaPnlJpy'])==selected-calc_c,'FROZEN_ROUTE')
        audited+=1
    group_checks={}
    for world in ('ALL_100','PRIMARY_FUNDED'):
        for arm in ('IM','R1'):
            subset=[v for k,v in paired.items() if k[0]==world and k[1]==arm]
            for group,test in (('ALL_ROUTES',lambda r:True),
                               ('<5',lambda r:dec(r['futureUpsidePctEvaluatorOnly'])<5),
                               ('5-10',lambda r:5<=dec(r['futureUpsidePctEvaluatorOnly'])<10),
                               ('>=10',lambda r:dec(r['futureUpsidePctEvaluatorOnly'])>=10),
                               ('>=5',lambda r:dec(r['futureUpsidePctEvaluatorOnly'])>=5)):
                chosen=[r for r in subset if test(r)]
                c=sum((dec(r['controlPnlJpy']) for r in chosen),Decimal(0))
                m=sum((dec(r['ccmgPnlJpy']) for r in chosen),Decimal(0))
                rd=sum((dec(r['routedDeltaPnlJpy']) for r in chosen),Decimal(0))
                pct=sum((100*(dec(r['ccmgPnlJpy'])-dec(r['controlPnlJpy']))/
                          dec(r['entryCostJpy']) for r in chosen),Decimal(0))/len(chosen)
                target=(result['values'][f'{world}:{arm}:ALL_ROUTES'] if group=='ALL_ROUTES'
                        else result['bands'][f'{world}:{arm}:{group}'])
                verify(len(chosen)==target['pairedN'] and m-c==dec(target['deltaPnlJpy']) and
                       rd==dec(target['routedDeltaPnlJpy']) and pct==dec(target['meanDeltaNetPp']),
                       'GROUP_REBUILD:'+world+':'+arm+':'+group)
                group_checks[f'{world}:{arm}:{group}']={'pairedN':len(chosen),
                    'deltaJpy':str(m-c),'meanDeltaNetPp':str(pct),'routedDeltaJpy':str(rd)}
    verify(result['bands']['ALL_100:R1:5-10']['routedDeltaPnlJpy'] is not None and
           dec(result['bands']['ALL_100:R1:5-10']['routedDeltaPnlJpy'])==-41500,
           'R1_5_10_WINNER_LOSS')
    for arm in ('IM','R1'):
        subset=[v for k,v in paired.items() if k[0]=='ALL_100' and k[1]==arm]
        negatives=sorted((dec(x['deltaPnlJpy']) for x in subset if dec(x['deltaPnlJpy'])<0))
        positives=[dec(x['deltaPnlJpy']) for x in subset if dec(x['deltaPnlJpy'])>0]
        concentration=result['concentration'][f'ALL_100:{arm}']
        verify(len(negatives)==concentration['negativeN'] and
               len(positives)==concentration['positiveN'] and
               -sum(negatives,Decimal(0))==dec(concentration['grossLossAbsoluteJpy']) and
               sum(positives,Decimal(0))==dec(concentration['grossGainJpy']),
               'INDEPENDENT_CONCENTRATION:'+arm)
        for top in (1,3,5,10):
            verify(-sum(negatives[:top],Decimal(0))==
                   dec(concentration['lossTopN'][str(top)]['absoluteJpy']),
                   'TOP_LOSS:'+arm+':'+str(top))
        for head in (5,10):
            for bin_number in range(10):
                decile=[x for x in subset if x[f'rank{head}Decile']==bin_number]
                published=result['rank'][arm][f'head{head}']['deciles'][str(bin_number)]
                verify(len(decile)==published['pairedN'] and
                       sum((dec(x['deltaPnlJpy']) for x in decile),Decimal(0))==
                       dec(published['deltaPnlJpy']),
                       'RANK_BIN_REBUILD:'+arm+':'+str(head)+':'+str(bin_number))
    opportunities=defaultdict(lambda:defaultdict(list))
    for (world,arm,_),r in paired.items():
        if world=='ALL_100':opportunities[r['opportunityId']][arm].append(r)
    cross=[v for v in opportunities.values() if len(v['IM'])==1 and len(v['R1'])==1]
    verify(len(cross)==result['crossArmOpportunity']['sameOpportunityKnownPairedN'],
           'CROSS_ARM_OPPORTUNITY_REBUILD')
    output={'schema':'phase57-post-prr-independent-audit-v1','status':'PASS',
        'independentMethod':'Raw CCMG saved Entry/exit prices plus independent R34 Decimal formula; no A1 accounting or summary functions imported',
        'sourceManifestHashesVerified':True,'reconstructedRowsN':audited,'pairedRowsN':len(paired),
        'groupChecks':group_checks,'a0A1AndIntentMasksVerified':True,
        'oldClosuresUntouched':True,'newEstimatorFits':0,'newPolicyReplays':0,
        'providerRequests':0,'restrictedPartitionsOpened':0,'orders':0}
    path=DEST/'INDEPENDENT_AUDIT.json'
    if path.exists():
        verify(load(path)==output,'INDEPENDENT_AUDIT_OUTPUT_DRIFT')
    else:
        path.write_text(json.dumps(output,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':'PASS','rows':audited,'paired':len(paired),
                      'auditSha256':digest(path)}))


if __name__=='__main__':main()
