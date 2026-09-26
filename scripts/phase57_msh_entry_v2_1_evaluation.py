"""Evaluator-only v2.1 anchor retention, fixed gates and descriptive attribution.

No fit, runtime feature generation, threshold search or portfolio policy lives here.
"""
import collections
import math
import statistics

from predict.research import phase57_msh_entry_long_v2_1_d30 as model
from scripts.phase57_msh_entry_v2_evaluation import entry_metrics, quantile, ratio_gate

LEVELS = (1, 2, 3, 5)


def distribution(values):
    return {'n':len(values), 'mean':statistics.mean(values) if values else None,
            'median':statistics.median(values) if values else None,
            'p90':quantile(values,.90), 'p95':quantile(values,.95),
            'ES95':statistics.mean(sorted(values,reverse=True)[:math.ceil(.05*len(values))]) if values else None}


def metrics(rows, decisions, baseline, labels, sessions, paths=None):
    b_ids = {r['eventId'] for r in baseline if r['state']=='ENTER'}
    a_ids = {r['eventId'] for r in decisions if r['state']=='ENTER'}
    if not a_ids <= b_ids:
        raise model.IntegrityError('V1_REFINEMENT_SUBSET_VIOLATION')
    out = entry_metrics(rows,decisions,labels,sessions,paths)
    out['legacySelectorWindowPreservationDiagnostic'] = out.pop('preservation')
    out['winnerRetention'] = {}
    for k in LEVELS:
        winners = {eid for eid in b_ids if labels[eid]['labelable'] and labels[eid]['mfePct'] >= k}
        hits = len(a_ids & winners)
        out['winnerRetention'][str(k)] = {'hits':hits,'baselineWinners':len(winners),
                                         'rate':hits/len(winners) if winners else None}
    out['D30'] = distribution([model.target_from_label(labels[eid]) for eid in a_ids if labels[eid]['labelable']])
    counts = out['tradesPerSymbol'].values()
    out['entrySymbolHHI'] = sum((n/len(a_ids))**2 for n in counts) if a_ids else None
    out['effectiveEntrySymbols'] = 1/out['entrySymbolHHI'] if out['entrySymbolHHI'] else None
    out['macroSymbolDenominator'] = len(out['symbolMeanD30'])
    out['baselineSymbolsEntirelyRejected'] = sorted({r['symbol'] for r in rows if r['selectorEventId'] in b_ids}
                                                  - set(out['tradesPerSymbol']))
    out['opportunityBoundsDiagnostic'] = {
        str(k):{'lower':out['precision'][str(k)]['hits']/len(a_ids) if a_ids else None,
                'upper':(out['precision'][str(k)]['hits']+out['unlabelableEnterCount'])/len(a_ids) if a_ids else None}
        for k in LEVELS}
    return out


def scalar_gate(name, value, limit, operator, **extra):
    return {'name':name,'candidate':value,'limit':limit,'operator':operator,
            'status':'INCONCLUSIVE' if value is None else ('PASS' if
                (value<=limit+1e-12 if operator=='<=' else value>=limit-1e-12) else 'FAIL'),**extra}


def coverage_gate(b,a,limit):
    x,y=b['coverageRate'],a['coverageRate']
    return scalar_gate('absoluteStrictLabelCoverageGapMax',abs(x-y) if x is not None and y is not None else None,
                       limit,'<=',baseline=x,acceptedCoverage=y)


def entry_gates(b,a,c):
    p=c['numericGates']['primary']
    gates=[]
    for k in (1,2):
        gates.append(ratio_gate(f'precision{k}RatioMin',b['precision'][str(k)]['rate'],
                               a['precision'][str(k)]['rate'],p[f'precision{k}RatioMin'],'>='))
    for k in (3,5):
        r=a['winnerRetention'][str(k)]
        gates.append(scalar_gate(f'winnerRetention{k}Min',r['rate'],p[f'winnerRetention{k}Min'],
                                 '>=',numerator=r['hits'],denominator=r['baselineWinners']))
    gates.extend([ratio_gate('adverseMeanRatioMax',b['meanD30'],a['meanD30'],p['adverseMeanRatioMax'],'<=',True),
                  ratio_gate('adverseES95RatioMax',b['ES95D30'],a['ES95D30'],p['adverseES95RatioMax'],'<='),
                  ratio_gate('throughputRatioMin',b['enterCount'],a['enterCount'],p['throughputRatioMin'],'>=')])
    gates.append(coverage_gate(b,a,c['numericGates']['guardrails']['absoluteStrictLabelCoverageGapMax']))
    return gates


def choose_threshold(results):
    if set(results)!={str(int(t)) for t in model.THRESHOLDS}:
        raise model.IntegrityError('EXACT_FOUR_THRESHOLDS_REQUIRED')
    eligible=[t for t in model.THRESHOLDS if all(g['status']=='PASS' for g in results[str(int(t))]['gates'])]
    return {'threshold':max(eligible) if eligible else None,
            'status':'SELECTED_INNER_ONLY' if eligible else 'NONE',
            'reason':'LARGEST_THRESHOLD_PASSING_ALL_7_PRIMARY_AND_COVERAGE' if eligible else
                     'NO_FIXED_THRESHOLD_PASSES_ALL_7_PRIMARY_AND_COVERAGE',
            'failedOrUnknownByThreshold':{k:[g['name']+':'+g['status'] for g in v['gates'] if g['status']!='PASS']
                                          for k,v in results.items()}}


def attribution(decisions,labels):
    """Nonexclusive diagnostic labels. Risk>=5 = severe landmark, never a gate.

    High opportunity is >=3; +5 is separately counted. Unknown outcome never
    becomes a correct/false decision. Missing-state skips are not direct vetoes.
    """
    anchors=[d for d in decisions if d.get('opportunityState')=='ENTER']
    detail=[]
    for d in anchors:
        lab=labels[d['eventId']]
        known=lab['labelable']
        risk=model.target_from_label(lab)
        mfe=lab['mfePct'] if known else None
        accepted=d['state']=='ENTER'; veto=d['reason']=='DIRECT_RISK_VETO'
        detail.append({'eventId':d['eventId'],'symbol':d['symbol'],'decisionTimestamp':d['decisionTimestamp'],
            'accepted':accepted,'directRiskVeto':veto,'decisionReason':d['reason'],
            'labelable':known,'labelReason':lab.get('reason'),'D30':risk,'MAE':-risk if known else None,'MFE':mfe,
            'correctRiskRejection':veto and known and risk>=5,
            'falseRiskRejection':{str(k):veto and known and mfe>=k for k in LEVELS},
            'falseRiskAcceptance':accepted and known and risk>=5,
            'goodAcceptance':accepted and known and mfe>=1 and risk<5,
            'missing':d.get('missing'),'predictedD30':d['predictedD30']})
    accepted=[x for x in detail if x['accepted'] and x['labelable']]
    rejected=[x for x in detail if x['directRiskVeto'] and x['labelable']]
    def strata(values):
        return dict(collections.Counter('BOTH' if x['missing']==[1,1] else 'ONE' if sum(x['missing'] or [])==1 else 'NONE' for x in values))
    counts={'anchors':len(detail),'riskAccepted':sum(x['accepted'] for x in detail),
        'directRiskVeto':sum(x['directRiskVeto'] for x in detail),
        'unsupportedOrInvalid':sum(not x['accepted'] and not x['directRiskVeto'] for x in detail),
        'correctRiskRejections':sum(x['correctRiskRejection'] for x in detail),
        'falseRiskRejections':{str(k):sum(x['falseRiskRejection'][str(k)] for x in detail) for k in LEVELS},
        'falseRiskAcceptances':sum(x['falseRiskAcceptance'] for x in detail),
        'goodAcceptances':sum(x['goodAcceptance'] for x in detail),
        'censoredUnknown':sum(not x['labelable'] for x in detail),
        'rejectedAdverseCounts':{str(k):sum(x['D30']>=k for x in rejected) for k in (2,5,10)}}
    a,r=distribution([x['D30'] for x in accepted]),distribution([x['D30'] for x in rejected])
    return {'definitions':'Nonexclusive: correct rejection/false acceptance D30>=5; good acceptance MFE>=1 and D30<5; winner rejects at +1/+2/+3/+5. Unsupported skips separate. Diagnostic only.',
            'counts':counts,'acceptedD30':a,'rejectedD30':r,
            'directRejectedMinusAcceptedMeanD30':r['mean']-a['mean'] if r['mean'] is not None and a['mean'] is not None else None,
            'acceptedMissing':strata([x for x in detail if x['accepted']]),
            'rejectedMissing':strata([x for x in detail if x['directRiskVeto']]),'records':detail}


def stability(pairs,required,n,name):
    records=[ratio_gate(str(key),b['meanD30'],a['meanD30'],1.,'<=') for key,b,a in pairs]
    defined=len(records)==n and all(g['status']!='INCONCLUSIVE' for g in records)
    return scalar_gate(name,sum(g['status']=='PASS' for g in records) if defined else None,required,'>=',
                       requiredPopulations=n,observedPopulations=len(records),groups=records)


def final_gates(b,a,c,chrono_pairs,cross_metrics,cross_pairs,attr):
    g=c['numericGates']['guardrails']; cs=c['numericGates']['crossSymbol']
    out=entry_gates(b,a,c)
    out += [ratio_gate('entrySymbolHHIRatioMax',b['entrySymbolHHI'],a['entrySymbolHHI'],g['entrySymbolHHIRatioMax'],'<='),
            stability(chrono_pairs,g['chronologicalNonWorseFoldsMin'],g['chronologicalFoldCount'],'chronologicalNonWorseFoldsMin'),
            scalar_gate('directRiskRejectedMinusAcceptedMeanD30Min',attr['directRejectedMinusAcceptedMeanD30'],g['directRiskRejectedMinusAcceptedMeanD30Min'],'>=')]
    x=cross_metrics
    cross=[ratio_gate('pooledMeanD30RatioMax',b['meanD30'],x['meanD30'],cs['pooledMeanD30RatioMax'],'<='),
           ratio_gate('macroSymbolMeanD30RatioMax',b['symbolMacroMeanD30'],x['symbolMacroMeanD30'],cs['macroSymbolMeanD30RatioMax'],'<='),
           stability(cross_pairs,cs['nonWorseGroupsMin'],cs['groups'],'nonWorseGroupsMin')]
    for k in (1,2):
        cross.append(ratio_gate(f'precision{k}RatioMin',b['precision'][str(k)]['rate'],x['precision'][str(k)]['rate'],cs[f'precision{k}RatioMin'],'>='))
    for k in (3,5):
        cross.append(scalar_gate(f'winnerRetention{k}Min',x['winnerRetention'][str(k)]['rate'],cs[f'winnerRetention{k}Min'],'>='))
    cross += [ratio_gate('throughputRatioMin',b['enterCount'],x['enterCount'],cs['throughputRatioMin'],'>='),
              coverage_gate(b,x,cs['absoluteStrictLabelCoverageGapMax'])]
    return {'chronological':out,'symbolDisjoint':cross}


def verdict(complete,gates):
    if not complete:
        return 'MSH_ENTRY_LONG_V2_1_DEVELOPMENT_BLOCKED'
    values=[g['status'] for group in gates.values() for g in group]
    if 'FAIL' in values:
        return 'MSH_ENTRY_LONG_V2_1_DEVELOPMENT_FAIL'
    if values and all(v=='PASS' for v in values):
        return 'MSH_ENTRY_LONG_V2_1_DEVELOPMENT_PASS'
    return 'MSH_ENTRY_LONG_V2_1_DEVELOPMENT_BLOCKED'
