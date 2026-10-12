"""Authorized Development runner for the immutable Entry v2 contract.

No tuning switches. An infeasible inner threshold stops that fold/replica before
outer refit or prediction. Missing predictions never become SKIP or zero profit.
"""
import argparse
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path
import subprocess

from predict.research import phase57_msh_entry_long_v2_d30 as model
from scripts import audit_phase57_msh_entry_v2_predevelopment as frozen
from scripts import phase57_long_capital_integration as ledger
from scripts.phase57_msh_entry_v2_evaluation import entry_metrics,entry_gates,choose_threshold,concentration,ratio_gate

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'docs/evidence/phase57-msh-entry-long-v2-development'
MODEL_SOURCES = ['predict/research/phase57_msh_entry_long_v2_d30.py',
    'scripts/phase57_msh_entry_v2_evaluation.py','scripts/phase57_msh_entry_v2_development.py',
    'scripts/phase57_msh_entry_v2_equal.mjs','scripts/test_phase57_msh_entry_v2_model.py',
    'scripts/test_phase57_msh_entry_v2_development.py']


def write(path,value):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as handle:
        handle.write(model.canonical(value)+b'\n')


def write_gz(path,value):
    with Path(path).open('xb') as handle:
        handle.write(gzip.compress(model.canonical(value)+b'\n',mtime=0))


def require_prefit(receipt):
    if receipt['status'] != 'PASS' or receipt['contractSHA'] != model.CONTRACT_SHA or not receipt['syntheticOnly']:
        raise model.IntegrityError('PREFIT_TEST_GATE_FAILED')
    for name in MODEL_SOURCES:
        if frozen.sha(ROOT/name) != receipt['implementationPins'][name]:
            raise model.IntegrityError('PREFIT_CODE_CHANGED:'+name)


def partition(rows,fold,c,group=None):
    sessions=c['universe']['sessions']
    inner=set(sessions[fold['innerFitOrdinals'][0]-1:fold['innerFitOrdinals'][1]])
    calibration=set(sessions[fold['innerCalibrationOrdinals'][0]-1:fold['innerCalibrationOrdinals'][1]])
    train=set(fold['trainDates']);evaluation=set(fold['evaluationDates'])
    allowed=lambda r:group is None or frozen.symbol_group(r['symbol']) != group
    held=lambda r:group is None or frozen.symbol_group(r['symbol']) == group
    fit=[r for r in rows if r['sessionDate'] in inner and allowed(r)]
    cal=[r for r in rows if r['sessionDate'] in calibration and allowed(r)]
    refit=[r for r in rows if r['sessionDate'] in train and allowed(r)]
    evaluate=[r for r in rows if r['sessionDate'] in evaluation and held(r)]
    audit={'sessionOverlap':0,'symbolSessionOverlap':0,'heldSymbolOverlap':0,'purgedInner':0,'purgedOuter':0}
    if not cal or not evaluate or not fit:
        raise model.FitError('INSUFFICIENT_SPLIT_SUPPORT')
    for name,left,right in [('inner',fit,cal),('outer',refit,evaluate)]:
        if {r['sessionDate'] for r in left} & {r['sessionDate'] for r in right}:
            raise model.IntegrityError('SESSION_OVERLAP')
        if {(r['symbol'],r['sessionDate']) for r in left} & {(r['symbol'],r['sessionDate']) for r in right}:
            raise model.IntegrityError('SYMBOL_SESSION_OVERLAP')
        next_start=min(model.timestamp(r['decisionTimestamp']) for r in right)
        # Same-session strict30m labels; requiring the entire label interval before
        # the next block also purges any overlapping same-symbol window.
        purged=[r for r in left if model.timestamp(r['decisionTimestamp'])+1800 >= next_start]
        audit['purgedInner' if name=='inner' else 'purgedOuter']=len(purged)
        ids={r['selectorEventId'] for r in purged}
        if name=='inner':fit=[r for r in left if r['selectorEventId'] not in ids]
        else:refit=[r for r in left if r['selectorEventId'] not in ids]
    if group is not None:
        trained={r['symbol'] for r in fit+cal+refit}
        held_symbols={r['symbol'] for r in evaluate}
        if trained & held_symbols:
            raise model.IntegrityError('HELD_SYMBOL_OVERLAP')
    return fit,cal,refit,evaluate,audit


def score_free_weights(events):
    rows=[{'eventId':e['selectorEventId'],'symbol':e['symbol'],
           'timestamp':ledger.iso(ledger.stamp(e['decisionTimestamp']))} for e in events]
    p=subprocess.run(['node','scripts/phase57_msh_entry_v2_equal.mjs'],input=json.dumps(rows),text=True,capture_output=True)
    if p.returncode:
        raise model.IntegrityError('SCORE_FREE_CONNECTOR_FAILED:'+p.stderr)
    return json.loads(p.stdout)


def exit_outcome(event):
    runtime=ledger.module('predict/long-only/phase57_long_exit_development_final.py','entry_v2_selected_exit')
    if event['expectedBars']==0:
        return {'status':'CENSORED','reason':'NO_REMAINING_REGULAR_BAR'}
    state=runtime.new_position(event['expectedBars'])
    for bar in event['future']:
        out=runtime.on_completed_bar(state,bar)
        if out['status']!='HOLD_RESEARCH_STATE':
            return out
    return {'status':'CENSORED','reason':'INCOMPLETE_TO_CALENDAR_CAP'}


def portfolio(decisions,paths,sessions,cash_contract,with_exclusions=True):
    ids={p['eventId'] for p in decisions if p['state']=='ENTER'}
    events=[paths[eid] for eid in sorted(ids)]
    replay=ledger.replay(events,sessions,'EQUAL_MAX3',score_free_weights(events),cash_contract)
    replay['symbolConcentrationDiagnostic']=concentration(replay['closedTrades'])
    replay['contributionScope']='FULL_CLOSED_STREAM' if replay['status']=='COMPLETE_REFERENCE_REPLAY' else 'CLOSED_ONLY_UNRESOLVED_EXPOSURE_NOT_FULL_PERFORMANCE'
    replay['exitResolvableCount']=sum(exit_outcome(e)['status']=='EXIT_REFERENCE' for e in events)
    replay['supportingExclusions']={}
    if with_exclusions:
        ordered=replay['symbolConcentrationDiagnostic']['positive']['orderedContributions']
        for n in (1,3):
            excluded={s for s,_ in ordered[:n]}
            chosen=[e for e in events if e['symbol'] not in excluded]
            diagnostic=ledger.replay(chosen,sessions,'EQUAL_MAX3',score_free_weights(chosen),cash_contract)
            replay['supportingExclusions']['top'+str(n)+'Symbols']={
                'excludedSymbols':sorted(excluded),'status':diagnostic['status'],
                'finalEquityJpy':diagnostic['finalEquityJpy'],'returnPct':diagnostic['totalReturnPct'],
                'profitFactor':diagnostic['trade']['profitFactor'],'maxDrawdownPct':diagnostic['maxDrawdownPct'],
                'scope':'RETROSPECTIVE_DIAGNOSTIC_NO_RULE; contributor ranking is closed-only if full stream unresolved'}
    return replay


def portfolio_gates(baseline,candidate,c):
    names=['portfolioNetPnlDeltaMinJpy','portfolioRequirePFImprovementOrDDImprovement',
           'portfolioProfitFactorRatioMin','portfolioMaxDrawdownRatioMax','positiveSymbolHHIRatioMax','negativeSymbolHHIRatioMax']
    limits={**c['numericGates']['primary'],**c['numericGates']['guardrails']}
    if candidate is None or baseline['status']!='COMPLETE_REFERENCE_REPLAY' or candidate['status']!='COMPLETE_REFERENCE_REPLAY':
        return [{'name':n,'status':'INCONCLUSIVE','limit':limits[n],'reason':'NO_COMPLETE_SELECTED_OOF_OR_UNPRICED_EXPOSURE'} for n in names]
    out=[]
    diff=candidate['finalEquityJpy']-baseline['finalEquityJpy']
    out.append({'name':names[0],'differenceJpy':diff,'limit':limits[names[0]],'status':'PASS' if diff>=-1e-6 else 'FAIL'})
    a,b=baseline['trade']['profitFactor'],candidate['trade']['profitFactor']
    pf_improves=(b=='INF' and a not in (None,'INF')) or (isinstance(a,(int,float)) and isinstance(b,(int,float)) and b>a+1e-12)
    dd_improves=candidate['maxDrawdownPct']<baseline['maxDrawdownPct']-1e-12
    out.append({'name':names[1],'status':'INCONCLUSIVE' if a is None or b is None else ('PASS' if pf_improves or dd_improves else 'FAIL')})
    if a=='INF' or b=='INF':
        pf={'name':names[2],'status':'INCONCLUSIVE' if a is None or b is None else ('FAIL' if a=='INF' and b!='INF' else 'PASS'),'reason':'INFINITE_PF_RULE'}
    else:pf=ratio_gate(names[2],a,b,limits[names[2]],'>=')
    out.append(pf)
    out.append(ratio_gate(names[3],baseline['maxDrawdownPct'],candidate['maxDrawdownPct'],limits[names[3]],'<='))
    for side,name in [('positive',names[4]),('negative',names[5])]:
        out.append(ratio_gate(name,baseline['symbolConcentrationDiagnostic'][side]['HHI'],candidate['symbolConcentrationDiagnostic'][side]['HHI'],limits[name],'<='))
    return out


def run_replica(rows,by_baseline,labels,paths,c,fold,group,fit_predict):
    name=f"chrono-{fold['fold']}" if group is None else f"symbol-{group}-fold-{fold['fold']}"
    fit_rows,cal,refit,evaluate,leak=partition(rows,fold,c,group)
    sessions=sorted({r['sessionDate'] for r in cal})
    b=entry_metrics(cal,[by_baseline[r['selectorEventId']] for r in cal],labels,sessions,paths)
    try:
        scored=fit_predict(fit_rows,cal,name+'-inner')
    except model.FitError as exc:
        return {'name':name,'fold':fold['fold'],'heldGroup':group,'leakageAudit':leak,
            'innerBaseline':b,'innerThresholdResults':{},'selection':{'threshold':None,'status':'FIT_FAILED_NO_MODEL_NO_FALLBACK','reason':str(exc)},
            'plannedEvaluationRows':len(evaluate),'outerPredictions':[],'outerDecisions':[],
            'outerFixedThresholdDiagnostics':{},'status':'INNER_FIT_FAILED'}
    all_results={}
    for t in model.THRESHOLDS:
        decisions=model.decide(scored,t)
        metrics=entry_metrics(cal,decisions,labels,sessions,paths)
        all_results[str(int(t))]={'threshold':t,'metrics':metrics,'gates':entry_gates(b,metrics,c)}
    selected=choose_threshold(all_results)
    replica={'name':name,'fold':fold['fold'],'heldGroup':group,'leakageAudit':leak,
        'innerBaseline':b,'innerThresholdResults':all_results,'selection':selected,
        'plannedEvaluationRows':len(evaluate),'outerPredictions':[],'outerDecisions':[],
        'outerFixedThresholdDiagnostics':{},'status':'SELECTION_INCONCLUSIVE_NO_CANDIDATE'}
    if selected['threshold'] is not None:
        try:
            scores=fit_predict(refit,evaluate,name+'-outer')
        except model.FitError as exc:
            replica['status']='OUTER_FIT_FAILED'
            replica['fitFailure']=str(exc)
            return replica
        replica['outerPredictions']=scores
        replica['outerDecisions']=model.decide(scores,selected['threshold'])
        replica['status']='OUTER_OOF_COMPLETE'
        eval_sessions=fold['evaluationDates']
        for t in model.THRESHOLDS:
            replica['outerFixedThresholdDiagnostics'][str(int(t))]=entry_metrics(evaluate,model.decide(scores,t),labels,eval_sessions,paths)
    print(json.dumps({'replica':name,'selectedThreshold':selected['threshold'],'outerRows':len(replica['outerPredictions'])}),flush=True)
    return replica


def main(output=BASE/'run',paths_file=BASE/'paths.json.gz'):
    frozen.audit()
    c=frozen.read(ROOT/frozen.CONTRACT)
    receipt=frozen.read(BASE/'prefit-tests.json');require_prefit(receipt)
    output=Path(output)
    if output.exists():
        raise model.IntegrityError('IMMUTABLE_RUN_OUTPUT_EXISTS')
    if not Path(paths_file).exists():
        raise model.IntegrityError('ALL3800_PATHS_NOT_AVAILABLE')
    if frozen.sha(Path(paths_file)) != Path(str(paths_file)+'.sha256').read_text().strip():
        raise model.IntegrityError('PATH_DIGEST_MISMATCH')
    payload=json.loads(gzip.decompress(Path(paths_file).read_bytes()))
    if payload['contractSHA']!=model.CONTRACT_SHA or not payload['legacy277Parity']:
        raise model.IntegrityError('PATH_SOURCE_MISMATCH')
    with gzip.open(ROOT/frozen.FEATURE_ROWS,'rt') as handle:rows=[json.loads(line) for line in handle]
    with gzip.open(ROOT/'docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/path-diagnostics.json.gz','rt') as handle:
        labels={r['selectorEventId']:r for r in json.load(handle)['events']}
    with gzip.open(ROOT/'docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/frozen-predictions.ndjson.gz','rt') as handle:
        saved={r['selectorEventId']:r for r in map(json.loads,handle)}
    paths={r['selectorEventId']:r for r in payload['events']}
    ids={r['selectorEventId'] for r in rows}
    if not (ids==set(labels)==set(saved)==set(paths) and len(ids)==3800):
        raise model.IntegrityError('SHARED_UNIVERSE_IDENTITY')
    inputs={r['selectorEventId']:model.extract_inputs(r) for r in rows}
    baseline=[{'eventId':r['selectorEventId'],'symbol':r['symbol'],'sessionDate':r['sessionDate'],
               'decisionTimestamp':r['decisionTimestamp'],'state':saved[r['selectorEventId']]['state']} for r in rows]
    by_baseline={p['eventId']:p for p in baseline}
    if sum(p['state']=='ENTER' for p in baseline)!=277:
        raise model.IntegrityError('FROZEN_V1_ENTER_IDENTITY')
    # Mandatory connector parity is checked before ANY Project fit.
    legacy_events=json.loads(gzip.decompress(ledger.PATHS.read_bytes()))['events']
    old_weights=ledger.weights(ledger.causal_envelopes(legacy_events,saved))['EQUAL_MAX3']
    if old_weights!=score_free_weights(legacy_events):
        raise model.IntegrityError('FROZEN_EQUAL_WEIGHT_PARITY')
    for e in legacy_events:
        p=paths[e['selectorEventId']]
        if p['future']!=e['future'] or p['expectedBars']!=e['expectedBars'] or p['decisionPrice']!=e['decisionPrice']:
            raise model.IntegrityError('LEGACY_PATH_PARITY')
    output.mkdir(parents=True);(output/'models').mkdir()
    fit_records=[];counters={'projectFitAttempts':0,'projectFits':0,'predictionRows':0,'predictionBatches':0,'thresholdPerformanceCandidates':4}
    def fit_predict(fit_rows,eval_rows,name):
        counters['projectFitAttempts']+=1
        a=model.fit([inputs[r['selectorEventId']] for r in fit_rows],labels)
        counters['projectFits']+=1
        file=output/'models'/(name+'.json')
        model.save_artifact(file,a)
        restored=model.load_artifact(file)
        predictions=model.predict(restored,[inputs[r['selectorEventId']] for r in eval_rows])
        counters['predictionRows']+=len(predictions);counters['predictionBatches']+=1
        fit_records.append({'name':name,'artifactSHA':a['artifactSHA'],'fileSHA':frozen.sha(file),
            'medians':a['medians'],'means':a['means'],'stds':a['stds'],'missingSeen':a['missingSeen'],
            'training':a['training'],'evaluationRows':len(eval_rows)})
        return predictions
    chrono=[run_replica(rows,by_baseline,labels,paths,c,f,None,fit_predict) for f in c['cv']['folds']]
    symbol=[run_replica(rows,by_baseline,labels,paths,c,f,g,fit_predict) for g in range(5) for f in c['cv']['folds']]
    eval_rows=[r for r in rows if r['sessionDate'] in c['universe']['sessions'][16:]]
    eval_sessions=c['universe']['sessions'][16:]
    bdec=[by_baseline[r['selectorEventId']] for r in eval_rows]
    bmetrics=entry_metrics(eval_rows,bdec,labels,eval_sessions,paths)
    streams={};gates=[]
    for name,replicas in [('chronological',chrono),('symbolDisjoint',symbol)]:
        decisions=[p for r in replicas for p in r['outerDecisions']]
        outids=[p['eventId'] for p in decisions]
        if len(outids)!=len(set(outids)):
            raise model.IntegrityError('OOF_DUPLICATE')
        complete=len(decisions)==3000 and all(r['status']=='OUTER_OOF_COMPLETE' for r in replicas)
        metrics=entry_metrics(eval_rows,decisions,labels,eval_sessions,paths) if complete else None
        streams[name]={'complete':complete,'plannedRows':3000,'oofRows':len(decisions),'duplicateCount':0,
            'missingPredictionCount':3000-len(decisions),'metrics':metrics,'decisions':decisions,
            'reason':None if complete else 'STOPPED_FOLDS_NO_ADMISSIBLE_INNER_THRESHOLD_NO_FALLBACK'}
    if streams['chronological']['complete']:
        gates=entry_gates(bmetrics,streams['chronological']['metrics'],c)
    else:
        gates=[{'name':n,'status':'INCONCLUSIVE','reason':'PRIMARY_SELECTED_OOF_INCOMPLETE'} for n in
            ['adverseMeanRatioMax','adverseES95RatioMax','preservation3RatioMin','preservation5RatioMin',
             'throughputRatioMin','precision1RatioMin','precision2RatioMin','absoluteStrictLabelCoverageGapMax']]
    cross_names=[n for n in c['numericGates']['primary'] if n.startswith('symbolDisjoint')]
    cross_group_metrics=[]
    if streams['symbolDisjoint']['complete']:
        cm=streams['symbolDisjoint']['metrics']
        cross_gates=[ratio_gate('symbolDisjointMeanD30RatioMax',bmetrics['meanD30'],cm['meanD30'],1.,'<='),
                     ratio_gate('symbolDisjointMacroMeanD30RatioMax',bmetrics['symbolMacroMeanD30'],cm['symbolMacroMeanD30'],1.,'<='),
                     ratio_gate('symbolDisjointThroughputRatioMin',bmetrics['enterCount'],cm['enterCount'],.8,'>=')]
        for k in (3,5):cross_gates.append(ratio_gate(f'symbolDisjointPreservation{k}RatioMin',bmetrics['preservation'][str(k)]['rate'],cm['preservation'][str(k)]['rate'],.9,'>='))
        ok=0;unknown=False
        for g in range(5):
            group_rows=[r for r in eval_rows if frozen.symbol_group(r['symbol'])==g]
            x=entry_metrics(group_rows,[p for p in streams['symbolDisjoint']['decisions'] if frozen.symbol_group(p['symbol'])==g],labels,eval_sessions,paths)
            b=entry_metrics(group_rows,[p for p in bdec if frozen.symbol_group(p['symbol'])==g],labels,eval_sessions,paths)
            test=ratio_gate('groupMeanD30',b['meanD30'],x['meanD30'],1.,'<=')
            ok+=test['status']=='PASS';unknown |= test['status']=='INCONCLUSIVE'
            cross_group_metrics.append({'group':g,'baseline':b,'v2':x,'gate':test})
        cross_gates.extend([{'name':'symbolDisjointNonWorseHashGroupsMin','count':ok,'limit':3,'status':'INCONCLUSIVE' if unknown else ('PASS' if ok>=3 else 'FAIL')},
                            {'name':'symbolDisjointHashGroupCount','count':5,'status':'INCONCLUSIVE' if unknown else 'PASS'}])
        cross_gates.extend([g|{'name':'symbolDisjointGuardrail:'+g['name']} for g in entry_gates(bmetrics,cm,c) if g['name'] in ['precision1RatioMin','precision2RatioMin','absoluteStrictLabelCoverageGapMax']])
    else:
        cross_gates=[{'name':n,'status':'INCONCLUSIVE','reason':'SYMBOL_SELECTED_OOF_INCOMPLETE'} for n in cross_names]
        cross_gates.extend([{'name':'symbolDisjointGuardrail:'+n,'status':'INCONCLUSIVE','reason':'SYMBOL_SELECTED_OOF_INCOMPLETE'} for n in ['precision1RatioMin','precision2RatioMin','absoluteStrictLabelCoverageGapMax']])
    cash_contract=frozen.read(ROOT/ledger.CONTRACT)
    bp=portfolio(bdec,paths,eval_sessions,cash_contract)
    cp=portfolio(streams['chronological']['decisions'],paths,eval_sessions,cash_contract) if streams['chronological']['complete'] else None
    gates+=cross_gates+portfolio_gates(bp,cp,c)
    incomplete=not streams['chronological']['complete'] or not streams['symbolDisjoint']['complete']
    if incomplete:
        verdict='MSH_ENTRY_LONG_V2_DEVELOPMENT_BLOCKED'
        reason='SELECTED_OOF_INCOMPLETE; no admissible inner threshold or fit failure stops affected folds. No fallback or complete selected candidate exists.'
    elif any(g['status']=='FAIL' for g in gates):
        verdict='MSH_ENTRY_LONG_V2_DEVELOPMENT_FAIL';reason='KNOWN_FROZEN_GATE_VIOLATION'
    elif any(g['status']=='INCONCLUSIVE' for g in gates):
        verdict='MSH_ENTRY_LONG_V2_DEVELOPMENT_BLOCKED';reason='FROZEN_GATE_UNMEASURABLE_NO_RELAXATION'
    else:
        verdict='MSH_ENTRY_LONG_V2_DEVELOPMENT_PASS';reason='ALL_FROZEN_PRIMARY_AND_GUARDRAILS_PASS'
    coverage={'candidates':3800,'labelable':sum(v['labelable'] for v in labels.values()),
        'v1FrozenEnter':277,'gateCandidates':3000,'gateSessions':60,
        'allCandidatesExitResolvable':sum(exit_outcome(e)['status']=='EXIT_REFERENCE' for e in paths.values()),
        'v1GateEnter':bmetrics['enterCount'],'v1GateStrict30m':bmetrics['strict30mCount'],
        'v1GateExitResolvable':bp['exitResolvableCount'],'v1PortfolioAccepted':bp['trade']['accepted'],
        'v1PortfolioUnresolved':bp['trade']['unresolved'],
        'v2GateEnter':streams['chronological']['metrics']['enterCount'] if streams['chronological']['complete'] else None,
        'v2GateStrict30m':streams['chronological']['metrics']['strict30mCount'] if streams['chronological']['complete'] else None,
        'v2PortfolioAccepted':cp['trade']['accepted'] if cp else None}
    report={'contractSHA':model.CONTRACT_SHA,'status':verdict,'reason':reason,'selectedThreshold':None,
        'selectionMeaning':'Per-fold nested thresholds; no full76 final candidate fit/promotion in this run. NONE if selected OOF incomplete.',
        'exposure':'HISTORICAL_DEVELOPMENT_IN_SAMPLE_OUTCOME_EXPOSED_CONDITIONAL_UNIVERSE',
        'currentAuthorization':'User 2026-09-17 instruction authorizes implementation/Development fit; frozen contract scope counters describe previous contract-only task.',
        'borderlineMapping':'Not emitted: Frozen Contract has no numeric BORDERLINE relaxation. Frozen INCONCLUSIVE maps to requested BLOCKED.',
        'pathSHA':frozen.sha(Path(paths_file)),'baselineFull76':entry_metrics(rows,baseline,labels,c['universe']['sessions'],paths),
        'baselineGate60':bmetrics,'chronological':chrono,'symbolDisjoint':symbol,'streams':streams,
        'fitRecords':fit_records,'coverage':coverage,'allFrozenGates':gates,'symbolGroupMetrics':cross_group_metrics,
        'portfolioBaseline':bp,'portfolioV2':cp,'equalAdapter277Parity':True,
        'runtimePredictorFeatureOrder':model.FEATURE_ORDER,'projectCounters':counters,
        'integrity':{'contractDeviations':0,'featureChanges':0,'modelTuning':0,'thresholdAdditions':0,
          'freshAccess':0,'entryOOSAccess':0,'exitOOSAccess':0,'prospectiveAccess':0,
          'jquantsRequests':0,'yahooRequests':0,'otherProviderRequests':0,'shortEvaluation':0,
          'sessionOverlap':0,'heldSymbolOverlap':0,'oofDuplicates':0},
        'executionUncertainty':'89180 one-JPY moves and repeated observations remain reference-price uncertainty; no symbol/raw-price filter or tick/spread proxy added.',
        'safety':c['safety'],'stop':True,'nextAction':'STOP; separate Root Cause Review/contract decision if BLOCKED or FAIL. No Fresh/OOS, no v2.1 rescue.'}
    write_gz(output/'development.json.gz',report)
    for name,value in streams.items():write_gz(output/(name+'-oof.json.gz'),value)
    write(output/'summary.json',{k:report[k] for k in ['contractSHA','status','reason','coverage','projectCounters','integrity','safety','stop','nextAction']})
    write(output/'fit-manifest.json',[{k:r[k] for k in ['name','artifactSHA','fileSHA','medians','means','stds','missingSeen','evaluationRows']}|{'trainingRows':r['training']['eligibleRows'],'excludedLabelRows':r['training']['excludedLabelRows']} for r in fit_records])
    print(json.dumps({'verdict':verdict,'coverage':coverage,'counters':counters}),flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default=str(BASE/'run'));parser.add_argument('--paths',default=str(BASE/'paths.json.gz'))
    args=parser.parse_args();main(args.output,args.paths)
