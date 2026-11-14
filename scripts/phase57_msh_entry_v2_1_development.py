"""One authorized, immutable v2.1 Development run. No redesign/tuning switches.

All calibration predictions, four decisions and gate denominators must be durable
BEFORE threshold selection. NONE stops that replica before outer refit/scoring.
"""
import collections
import gzip
import json
from pathlib import Path

from predict.research import phase57_msh_entry_long_v2_1_d30 as model
from scripts import audit_phase57_msh_entry_v2_1_predevelopment as frozen
from scripts import phase57_msh_entry_v2_1_evaluation as ev
from scripts import phase57_msh_entry_v2_development as reuse

ROOT=frozen.ROOT
BASE=ROOT/'docs/evidence/phase57-msh-entry-long-v2-1-development'
PATHS=ROOT/'docs/evidence/phase57-msh-entry-long-v2-development/paths.json.gz'
MODEL_SOURCES=['predict/research/phase57_msh_entry_long_v2_1_d30.py',
    'scripts/phase57_msh_entry_v2_1_evaluation.py','scripts/phase57_msh_entry_v2_1_development.py',
    'scripts/test_phase57_msh_entry_v2_1_runtime.py']
write=reuse.write
write_gz=reuse.write_gz
partition=reuse.partition


def require_prefit(receipt):
    if receipt['status']!='PASS' or receipt['contractSHA']!=model.CONTRACT_SHA or not receipt['syntheticOnly']:
        raise model.IntegrityError('PREFIT_TEST_GATE_FAILED')
    for path in MODEL_SOURCES:
        if frozen.sha(ROOT/path)!=receipt['implementationPins'][path]:
            raise model.IntegrityError('PREFIT_CODE_CHANGED:'+path)


def baseline_for(rows,saved):
    return [{'eventId':r['selectorEventId'],'symbol':r['symbol'],'sessionDate':r['sessionDate'],
             'decisionTimestamp':r['decisionTimestamp'],'state':saved[r['selectorEventId']]['state'],
             'reason':saved[r['selectorEventId']]['reason']} for r in rows]


def decision_inputs(rows):
    return [model.extract_inputs(r) for r in rows]


def anchors(rows,saved):
    return [r for r in rows if saved[r['selectorEventId']]['state']=='ENTER']


def run_replica(rows,saved,labels,paths,c,fold,group,fit_predict,persist):
    name=f"chrono-{fold['fold']}" if group is None else f"symbol-{group}-fold-{fold['fold']}"
    fit,cal,refit,evaluate,leak=partition(rows,fold,c,group)
    bdec=baseline_for(cal,saved)
    sessions=c['universe']['sessions'][fold['innerCalibrationOrdinals'][0]-1:fold['innerCalibrationOrdinals'][1]]
    b=ev.metrics(cal,bdec,bdec,labels,sessions,paths)
    replica={'name':name,'fold':fold['fold'],'heldGroup':group,'leakageAudit':leak,
        'innerBaseline':b,'innerThresholdResults':{},'outerPredictions':[],'outerDecisions':[],
        'outerMetrics':None,'outerBaseline':None,'outerAttribution':None,'plannedEvaluationRows':len(evaluate),
        'splitIds':{key:[r['selectorEventId'] for r in value] for key,value in
                    [('innerFit',fit),('innerCalibration',cal),('outerTrain',refit),('evaluation',evaluate)]}}
    # Split identities, source statuses and loss exclusions are persisted first.
    persist(name+'-split',replica['splitIds']|{'leakageAudit':leak,
        'fitAnchorIds':[r['selectorEventId'] for r in anchors(fit,saved)],
        'fitLabelExcluded':[{ 'eventId':r['selectorEventId'],'reason':labels[r['selectorEventId']].get('reason')}
            for r in anchors(fit,saved) if not labels[r['selectorEventId']]['labelable']]})
    try:
        scores=fit_predict(anchors(fit,saved),anchors(cal,saved),name+'-inner')
    except model.FitError as exc:
        replica.update(status='INNER_FIT_FAILED',selection={'threshold':None,'status':'FIT_FAILED','reason':str(exc)})
        persist(name+'-result',replica)
        return replica
    all_results={}
    inputs=decision_inputs(cal)
    for t in model.THRESHOLDS:
        dec=model.decide(inputs,saved,scores,t)
        met=ev.metrics(cal,dec,bdec,labels,sessions,paths)
        all_results[str(int(t))]={'threshold':t,'metrics':met,'gates':ev.entry_gates(b,met,c),
                                 'decisions':dec,'attribution':ev.attribution(dec,labels)}
    # Exclusive write raises on failure. Selection cannot run without this receipt.
    persisted=persist(name+'-calibration',{'baseline':b,'predictions':scores,'thresholds':all_results,
        'candidateIdentities':[{'eventId':r['selectorEventId'],'symbol':r['symbol'],'sessionDate':r['sessionDate'],
             'decisionTimestamp':r['decisionTimestamp'],'decisionPrice':r['decisionPrice'],
             'originalRiskFields':{k:r['features'][k] for k in model.FEATURE_ORDER[:2]},
             'opportunity':{k:saved[r['selectorEventId']][k] for k in ['state','reason','expectedClass']}} for r in cal]})
    if not persisted:
        raise model.IntegrityError('PERSISTENCE_REQUIRED_BEFORE_SELECTION')
    selected=ev.choose_threshold(all_results)
    replica.update(innerThresholdResults=all_results,selection=selected,status='NONE_NO_OUTER_MODEL',
                   calibrationPersistenceSHA=persisted)
    # Durable selected tau before outer refit; outer outcomes cannot select it.
    persist(name+'-selection',selected|{'calibrationPersistenceSHA':persisted})
    if selected['threshold'] is not None:
        try:
            scores=fit_predict(anchors(refit,saved),anchors(evaluate,saved),name+'-outer')
        except model.FitError as exc:
            replica.update(status='OUTER_FIT_FAILED',fitFailure=str(exc))
        else:
            dec=model.decide(decision_inputs(evaluate),saved,scores,selected['threshold'])
            eb=baseline_for(evaluate,saved)
            replica.update(status='OUTER_OOF_COMPLETE',outerPredictions=scores,outerDecisions=dec,
                outerMetrics=ev.metrics(evaluate,dec,eb,labels,fold['evaluationDates'],paths),
                outerBaseline=ev.metrics(evaluate,eb,eb,labels,fold['evaluationDates'],paths),
                outerAttribution=ev.attribution(dec,labels))
    persist(name+'-result',replica)
    print(json.dumps({'replica':name,'threshold':selected['threshold'],'status':replica['status']}),flush=True)
    return replica


def unknown_gates(c):
    # Counts are structural constants; all performance constraints explicitly unknown.
    return {scope:[{'name':n,'limit':v,'status':'INCONCLUSIVE','reason':'SELECTED_OOF_INCOMPLETE'}
                   for n,v in values.items()] for scope,values in
            [('chronological',c['numericGates']['primary']|c['numericGates']['guardrails']),
             ('symbolDisjoint',c['numericGates']['crossSymbol'])]}


def main():
    audit,split_plan,exclusions=frozen.audit()
    c=frozen.read(ROOT/frozen.CONTRACT)
    require_prefit(frozen.read(BASE/'prefit-tests.json'))
    output=BASE/'run'
    if output.exists():
        raise model.IntegrityError('IMMUTABLE_RUN_OUTPUT_EXISTS')
    def lines(path):
        with gzip.open(ROOT/path,'rt') as h:return [json.loads(line) for line in h]
    rows=lines(frozen.FEATURES)
    saved={r['selectorEventId']:r for r in lines(frozen.PREDICTIONS)}
    labels={r['selectorEventId']:r for r in json.loads(gzip.decompress((ROOT/frozen.LABELS).read_bytes()))['events']}
    payload=json.loads(gzip.decompress(PATHS.read_bytes()))
    if frozen.sha(PATHS)!=c['sourcePins'][str(PATHS.relative_to(ROOT))] or not payload['legacy277Parity']:
        raise model.IntegrityError('PATH_SOURCE_MISMATCH')
    paths={r['selectorEventId']:r for r in payload['events']}
    ids={r['selectorEventId'] for r in rows}
    if not (ids==set(saved)==set(labels)==set(paths) and len(ids)==3800):
        raise model.IntegrityError('SHARED_UNIVERSE_IDENTITY')
    frozen.shadow_anchor_audit(rows,saved)
    inputs={r['selectorEventId']:model.extract_inputs(r) for r in rows}
    legacy=json.loads(gzip.decompress(reuse.ledger.PATHS.read_bytes()))['events']
    old_weights=reuse.ledger.weights(reuse.ledger.causal_envelopes(legacy,saved))['EQUAL_MAX3']
    if old_weights!=reuse.score_free_weights(legacy):
        raise model.IntegrityError('FROZEN_EQUAL_PARITY')
    target_checks=0
    for e in legacy:
        p=paths[e['selectorEventId']]
        if any(p[k]!=e[k] for k in ['future','expectedBars','decisionPrice']):
            raise model.IntegrityError('FROZEN_PATH_PARITY')
        lab=labels[e['selectorEventId']]
        if lab['labelable']:
            bars=p['future'][:6]
            if len(bars)!=6 or any(b['missing'] for b in bars):
                raise model.IntegrityError('TARGET_PATH_WIRING')
            path_d=max(0.,-min(b['l'] for b in bars))
            if abs(path_d-model.target_from_label(lab))>1e-9:
                raise model.IntegrityError('TARGET_PATH_WIRING')
            target_checks+=1
    if target_checks!=181:
        raise model.IntegrityError('TARGET_LABELABLE_COUNT')
    output.mkdir();(output/'models').mkdir();(output/'units').mkdir()
    write(output/'source-audit.json',{'contract':audit,'splitPlan':split_plan,'targetPathChecks':target_checks,
                                    'equalNoVetoParity277':True,'pathsSHA':frozen.sha(PATHS)})
    write(output/'anchor-labelability-ledger.json',exclusions)
    fits=[];counters={'fitAttempts':0,'successfulFits':0,'innerFits':0,'outerFits':0,
                     'riskPredictionRecords':0,'numericRiskPredictions':0,'thresholdEvaluations':0}
    def persist(name,value):
        path=output/'units'/(name+'.json.gz');write_gz(path,value)
        return frozen.sha(path)
    def fit_predict(fit_rows,evaluate,name):
        counters['fitAttempts']+=1
        a=model.fit([inputs[r['selectorEventId']] for r in fit_rows],labels)
        counters['successfulFits']+=1;counters['innerFits' if name.endswith('-inner') else 'outerFits']+=1
        file=output/'models'/(name+'.json');model.save_artifact(file,a)
        restored=model.load_artifact(file)
        scores=model.predict(restored,[inputs[r['selectorEventId']] for r in evaluate])
        counters['riskPredictionRecords']+=len(scores)
        counters['numericRiskPredictions']+=sum(p['status']=='SCORED' for p in scores)
        persist(name+'-scores',scores)
        record={'name':name,'artifactSHA':a['artifactSHA'],'fileSHA':frozen.sha(file),
                'evaluationAnchorRows':len(evaluate),**{k:a[k] for k in
                 ['medians','means','stds','missingSeen','coefficients','intercept','training']}}
        fits.append(record)
        return scores
    chrono=[run_replica(rows,saved,labels,paths,c,f,None,fit_predict,persist) for f in c['cv']['folds']]
    cross=[run_replica(rows,saved,labels,paths,c,f,g,fit_predict,persist) for g in range(5) for f in c['cv']['folds']]
    counters['thresholdEvaluations']=sum(len(r['innerThresholdResults']) for r in chrono+cross)
    # Baseline window diagnostics are available even when no candidate model exists.
    for replica in chrono+cross:
        if replica['outerBaseline'] is None:
            f=c['cv']['folds'][replica['fold']-1]
            er=partition(rows,f,c,replica['heldGroup'])[3]
            bd=baseline_for(er,saved)
            replica['outerBaseline']=ev.metrics(er,bd,bd,labels,f['evaluationDates'],paths)
    sessions=c['universe']['sessions'][16:]
    erows=[r for r in rows if r['sessionDate'] in sessions]
    bdec=baseline_for(erows,saved)
    bm=ev.metrics(erows,bdec,bdec,labels,sessions,paths)
    streams={}
    for name,replicas in [('chronological',chrono),('symbolDisjoint',cross)]:
        dec=[d for r in replicas for d in r['outerDecisions']]
        pred=[p for r in replicas for p in r['outerPredictions']]
        if len({d['eventId'] for d in dec})!=len(dec):
            raise model.IntegrityError('OOF_DUPLICATE')
        complete=all(r['status']=='OUTER_OOF_COMPLETE' for r in replicas) and len(dec)==3000
        scored_ids={d['eventId'] for d in dec}
        # Missing OOF decisions are null/UNAVAILABLE, never invented SKIP decisions.
        by_dec={d['eventId']:d for d in dec}
        status_ledger=[{'eventId':r['selectorEventId'],'status':'OOF_AVAILABLE' if r['selectorEventId'] in scored_ids else
                       'UNAVAILABLE_NO_SELECTED_OUTER_MODEL','state':by_dec.get(r['selectorEventId'],{}).get('state')} for r in erows]
        streams[name]={'complete':complete,'plannedDecisionRows':3000,'oofDecisionRows':len(dec),
            'oofRiskPredictionRecords':len(pred),'numericRiskPredictions':sum(p['status']=='SCORED' for p in pred),
            'duplicates':0,'unavailableDecisionRows':3000-len(dec),'decisions':dec,'statusLedger':status_ledger,
            'metrics':ev.metrics(erows,dec,bdec,labels,sessions,paths) if complete else None,
            'attribution':ev.attribution(dec,labels) if complete else None,
            'reason':None if complete else 'NO_COMPLETE_SELECTED_OOF_NO_FALLBACK'}
    group_metrics=[];chrono_metrics=[]
    for r in chrono:
        chrono_metrics.append({'fold':r['fold'],'status':r['status'],'baseline':r['outerBaseline'],
                               'v21':r['outerMetrics']})
    if streams['symbolDisjoint']['complete']:
        for g in range(5):
            subset=[r for r in erows if frozen.symbol_group(r['symbol'])==g]
            bd=baseline_for(subset,saved)
            ad=[d for d in streams['symbolDisjoint']['decisions'] if frozen.symbol_group(d['symbol'])==g]
            group_metrics.append({'group':g,'baseline':ev.metrics(subset,bd,bd,labels,sessions,paths),
                                  'v21':ev.metrics(subset,ad,bd,labels,sessions,paths)})
    complete=all(s['complete'] for s in streams.values())
    gates=unknown_gates(c)
    if complete:
        gates=ev.final_gates(bm,streams['chronological']['metrics'],c,
            [(r['fold'],r['baseline'],r['v21']) for r in chrono_metrics],streams['symbolDisjoint']['metrics'],
            [(r['group'],r['baseline'],r['v21']) for r in group_metrics],streams['chronological']['attribution'])
    verdict=ev.verdict(complete,gates)
    cash=frozen.read(ROOT/reuse.ledger.CONTRACT)
    bp=reuse.portfolio(bdec,paths,sessions,cash)
    cp=reuse.portfolio(streams['chronological']['decisions'],paths,sessions,cash) if streams['chronological']['complete'] else None
    full=baseline_for(rows,saved)
    execution=[]
    for r in anchors(erows,saved):
        eid=r['selectorEventId'];out=reuse.exit_outcome(paths[eid]);lab=labels[eid]
        execution.append({'eventId':eid,'symbol':r['symbol'],'price':r['decisionPrice'],
            'strictMFE':lab.get('mfePct') if lab['labelable'] else None,'exitReference':out,
            'role':'DIAGNOSTIC_ONLY_NOT_EXECUTABILITY_PROOF'})
    coverage={'conditionalCandidates':3800,'sourceLabelable':1828,'rawScoreQualified':353,
        'stateConstrainedAnchors':277,'riskLabelable':181,'riskUnlabelable':96,
        'unlabelableReasons':c['universe']['unlabelableReasons'],'outerCandidateIds':3000,
        'outerV1Anchors':bm['enterCount'],'outerV1Labelable':bm['strict30mCount'],
        'outerV1ExitResolvable':bp['exitResolvableCount'],'v1PortfolioAccepted':bp['trade']['accepted'],
        'v1Unresolved':bp['trade']['unresolved'],
        'v21Enter':streams['chronological']['metrics']['enterCount'] if streams['chronological']['complete'] else None,
        'v21ExitResolvable':cp['exitResolvableCount'] if cp else None,
        'v21PortfolioAccepted':cp['trade']['accepted'] if cp else None}
    report={'contractSHA':model.CONTRACT_SHA,'verdict':verdict,'verdictScope':'ENTRY_REFINEMENT_ONLY',
        'reason':'SELECTED_OOF_INCOMPLETE_NO_ADMISSIBLE_INNER_THRESHOLD_OR_FIT_FAILURE' if not complete else 'FROZEN_GATES_APPLIED',
        'exposure':'HISTORICAL_DEVELOPMENT_IN_SAMPLE_OUTCOME_EXPOSED; OOF independence applies new Risk only, not exposed upstream',
        'selectionScope':'Nested per-fold threshold; no global/deployment threshold or full76 candidate refit authorized',
        'macroMetricInterpretation':'Use detailed metrics.macroSymbolMeanD30 per-arm observed-symbol denominator; no imputation for rejected symbols. applicationScopes stale fixed-set phrase cannot override the explicit definition.',
        'sourceHead':'a575f27731e879c1c1d5ed90d42f3c0bade3d996',
        'baselineFull76':ev.metrics(rows,full,full,labels,c['universe']['sessions'],paths),
        'baselineGate60':bm,'chronological':chrono,'symbolDisjoint':cross,'streams':streams,
        'chronologicalMetrics':chrono_metrics,'symbolGroupMetrics':group_metrics,'allFrozenGates':gates,
        'fitRecords':fits,'coverage':coverage,'projectCounters':counters,
        'portfolioBaseline':bp,'portfolioV21':cp,'portfolioRole':c['portfolio'],
        'executionDiagnostic':execution,'integrity':{'contractDeviations':0,'featureChanges':0,'opportunityChanges':0,
            'modelTuning':0,'thresholdAdditions':0,'gateChanges':0,'retimedEntry':0,'newV1SkipRecoveries':0,
            'sessionLeakage':0,'heldSymbolLeakage':0,'oofDuplicates':0,'freshAccess':0,'entryOosAccess':0,
            'exitOosAccess':0,'prospectiveAccess':0,'jQuantsPriceRequests':0,'yahooPriceRequests':0,
            'otherProviderPriceRequests':0,'shortEvaluation':0},'safety':c['safety'],
        'stop':True,'nextAction':'STOP. Separate instruction: BLOCKED -> blocker resolution contract; FAIL -> v2.1 Root Cause Review; PASS -> evidence/candidate freeze. No Fresh/OOS in this work.'}
    write_gz(output/'development.json.gz',report)
    for name,value in streams.items():write_gz(output/(name+'-oof.json.gz'),value)
    write(output/'fit-manifest.json',fits)
    write(output/'summary.json',{k:report[k] for k in ['contractSHA','verdict','reason','coverage','projectCounters','integrity','safety','nextAction']})
    print(json.dumps({'verdict':verdict,'coverage':coverage,'counters':counters}),flush=True)
    return report


if __name__=='__main__':
    main()
