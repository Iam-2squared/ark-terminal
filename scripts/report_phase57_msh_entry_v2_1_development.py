"""Render the immutable saved v2.1 run. No fit, prediction or new policy."""
import collections
import csv
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'docs/evidence/phase57-msh-entry-long-v2-1-development'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def number(v,n=4):return 'UNKNOWN' if v is None else f'{v:.{n}f}'
def pct(v):return 'UNKNOWN' if v is None else f'{v*100:.2f}%'
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+
                     ['| '+' | '.join(map(str,row))+' |' for row in rows])
def save_csv(name,rows):
    with (BASE/name).open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def main():
    r=json.loads(gzip.decompress((BASE/'run/development.json.gz').read_bytes()))
    c=json.loads((ROOT/'predict/research/phase57-msh-entry-long-v2-1-predevelopment-contract-v1.json').read_text())
    units=r['chronological']+r['symbolDisjoint']
    thresholds=[];gates=[];attribution=[];models=[]
    for unit in units:
        b=unit['innerBaseline']
        for t in [1,2,5,10]:
            result=unit['innerThresholdResults'][str(t)];m=result['metrics'];counts=result['attribution']['counts']
            x={'unit':unit['name'],'scope':'INNER_CALIBRATION_ONLY_NOT_OUTER_OOF','fold':unit['fold'],
                'heldGroup':unit['heldGroup'],'threshold':t,'selected':False,'baselineEnter':b['enterCount'],
                'enterCount':m['enterCount'],'enterPerSession':m['enterPerSession'],'uniqueSymbols':m['uniqueSymbols'],
                'strict30mCount':m['strict30mCount'],'unknownCount':m['unlabelableEnterCount'],
                'coverageRate':m['coverageRate'],'entrySymbolHHI':m['entrySymbolHHI'],
                'baselineMeanD30':b['meanD30'],'meanD30':m['meanD30'],
                'meanD30ImprovementPct':100*(1-m['meanD30']/b['meanD30']) if m['meanD30'] is not None and b['meanD30'] else None,
                'medianD30':m['D30']['median'],'D30p90':m['D30']['p90'],'D30p95':m['D30']['p95'],
                'D30ES95':m['ES95D30'],'MAEmedian':m['MAE']['median'],'MAEp05':m['MAE']['p05'],
                'MAEworst':m['MAE']['worst'],'MFEmean':m['MFE']['mean'],'MFEmedian':m['MFE']['median'],
                'MAEleMinus2':m['adverseCounts']['2'],'MAEleMinus5':m['adverseCounts']['5'],'MAEleMinus10':m['adverseCounts']['10']}
            for k in (1,2,3,5):
                x[f'precision{k}']=m['precision'][str(k)]['rate'];x[f'precision{k}Hits']=m['precision'][str(k)]['hits']
                x[f'anchorPreservation{k}']=m['winnerRetention'][str(k)]['rate']
                x[f'baselineWinners{k}']=m['winnerRetention'][str(k)]['baselineWinners']
                x[f'falseRiskRejected{k}']=counts['falseRiskRejections'][str(k)]
            x.update(correctRiskRejections=counts['correctRiskRejections'],falseRiskAcceptances=counts['falseRiskAcceptances'],
                     goodAcceptances=counts['goodAcceptances'],censoredUnknown=counts['censoredUnknown'],
                     throughput=m['enterCount']/b['enterCount'],
                     failedOrUnknown=';'.join(g['name']+':'+g['status'] for g in result['gates'] if g['status']!='PASS'))
            thresholds.append(x)
            for g in result['gates']:
                gates.append({'scope':unit['name'],'threshold':t,'gate':g['name'],'status':g['status'],
                              'values':json.dumps(g,sort_keys=True)})
            for a in result['attribution']['records']:
                attribution.append({'unit':unit['name'],'threshold':t,**a})
    for scope,gg in r['allFrozenGates'].items():
        for g in gg:gates.append({'scope':'FINAL_'+scope,'threshold':None,'gate':g['name'],'status':g['status'],'values':json.dumps(g,sort_keys=True)})
    save_csv('all-threshold-metrics.csv',thresholds);save_csv('all-frozen-gates.csv',gates)
    (BASE/'risk-decisions-diagnostic.ndjson.gz').write_bytes(gzip.compress(b''.join((json.dumps(a,sort_keys=True,separators=(',',':'))+'\n').encode() for a in attribution),mtime=0))
    for f in r['fitRecords']:
        tr=f['training']
        models.append({'unit':f['name'],'fitAnchors':tr['candidateRows'],'labelledFitRows':tr['eligibleRows'],
            'excludedLabels':tr['excludedLabelRows'],'symbols':len(tr['symbols']),'symbolSessions':tr['symbolSessionCount'],
            'weightSum':tr['weightSum'],'largestSymbolWeight':tr['largestSymbolWeightShare'],
            'largestSymbolSessionWeight':tr['largestSymbolSessionWeightShare'],
            'momentumMissing':tr['missingCounts'][0],'pullbackMissing':tr['missingCounts'][1],'bothMissing':tr['bothMissingCount'],
            'momentumMedian':f['medians'][0],'pullbackMedian':f['medians'][1],
            'momentumMean':f['means'][0],'pullbackMean':f['means'][1],'momentumStd':f['stds'][0],'pullbackStd':f['stds'][1],
            'intercept':f['intercept'],'betaMomentum':f['coefficients'][0],'betaPullback':f['coefficients'][1],
            'betaMomentumMissing':f['coefficients'][2],'betaPullbackMissing':f['coefficients'][3],
            'objective':tr['objective'],'residualInf':tr['normalEquationResidualInf'],
            'artifactSHA':f['artifactSHA'],'fileSHA':f['fileSHA']})
    save_csv('all-models-medians-weights.csv',models)
    brief=[['Verdict',r['verdict']],['Contract SHA',r['contractSHA']],
        ['Branch','research/phase57-long-only-cash-equity'],['PR','https://github.com/Iam-2squared/ark-terminal/pull/587 (Draft/unmerged)'],
        ['Source / freeze head',r['sourceHead']],['Latest main at start','c48be22db7deef286b0bb5dc1951964431145908'],
        ['Final head / CI','Containing research commit; exact final head and completed GitHub checks reported with delivery. No main merge.'],
        ['Dataset','2024-09-17..2025-01-09; 76 Historical / Development / IN-SAMPLE / Outcome-exposed sessions'],
        ['Conditional universe','3,800 events / 760 timestamps; 353 raw-qualified / 277 v1 anchors / 181 labelable / 96 unknown'],
        ['Primary outer scope','60 sessions / 3,000 candidate IDs / 232 v1 anchors / 159 labelable; warmup16 excluded in both arms'],
        ['Project fits','24 inner attempted / 24 success / 0 outer'],['Risk predictions','825 numeric inner-calibration records across repeated folds/groups; not 825 independent trades'],
        ['Threshold evaluations','96 = 24 units × {1,2,5,10}'],['Selection','NONE in all24 units'],
        ['Selected OOF','0 numerical predictions / 0 decisions; 3,000 UNAVAILABLE status records per scope, not fabricated SKIPs'],
        ['v2.1 selected ENTER / Portfolio','UNKNOWN / NOT_AVAILABLE; not 0 trades or 0% return'],
        ['Prefit tests','48 PASS before the single Project run; tests are synthetic/static only'],
        ['Budget SHA',c['dataProtection']['globalBudgetSHA']]]
    lines=['# Phase57 MSH-Entry LONG v2.1 Development — BLOCKED','',
        '**MSH_ENTRY_LONG_V2_1_DEVELOPMENT_BLOCKED**. The immutable experiment completed all24 inner fits and96 fixed-threshold evaluations. No threshold passed every precommitted inner condition in any unit. Contract requires stopping each replica before outer refit; no selected OOF or candidate Portfolio exists. This is not an implementation exception, a completed OOF FAIL, or evidence that all Risk refinement architectures fail.','',table(['Item','Result'],brief),'',
        '## What the fixed thresholds did','',
        'These are **chronological INNER calibration** results, not outer OOF. Windows overlap across expanding folds; do not sum them as independent evidence. Threshold5 and10 reproduce every baseline anchor in all24 units and therefore provide0% mean-D30 improvement. Threshold1 produces no labelable accepted observations in all24 units. Threshold2 either removes too many anchors/winners or fails another frozen condition. No new threshold was tried.','']
    lines.append(table(['Fold','Threshold','v1→v2.1 ENTER','strict N','Mean D30','D30 improvement','+1 Precision','+2 Precision','+3 retention','+5 retention','Throughput','Non-PASS gates'],[
        [x['fold'],x['threshold'],f"{x['baselineEnter']}→{x['enterCount']}",x['strict30mCount'],number(x['meanD30']),number(x['meanD30ImprovementPct'],2)+'%',pct(x['precision1']),pct(x['precision2']),pct(x['anchorPreservation3']),pct(x['anchorPreservation5']),pct(x['throughput']),x['failedOrUnknown']]
        for x in thresholds if x['heldGroup'] is None]))
    lines+=['','F1 threshold2 improves meanD30 by18.83%, but +1 precision is66.67% versus80%, throughput75% versus required80%, and strict-label coverage gap8.33pp exceeds5pp. +3/+5 retention is100% in that small calibration sample (two winners each). F2 threshold2 accepts2 anchors but neither has a strict30m label; F3/F4 accept none. Unknown outcomes are not labelled safe.','',
        'All96 results, precision/preservation1/2/3/5, D30/MAE/MFE distributions, tail counts, symbols and attribution: [all-threshold-metrics.csv](all-threshold-metrics.csv). Every numeric inner and final gate: [all-frozen-gates.csv](all-frozen-gates.csv).','',
        '## All fixed selection units','',table(['Unit','Fit labels / anchors','Calibration labels / anchors','Threshold','Outer status'],[
            [u['name'],f"{f['training']['eligibleRows']}/{f['training']['candidateRows']}",f"{u['innerBaseline']['strict30mCount']}/{u['innerBaseline']['enterCount']}",'NONE',u['status']]
            for u,f in zip(units,r['fitRecords'])]),'',
        'Chronological4 and hash-complement20 models use the same family. Held groups are excluded from fitting, imputation/scaling and calibration. No new split, sparse-group rebalance, symbol-specific exception or outer fallback. Actual session/symbol leakage0. Outer OOF duplicates0; OOF performance is unmeasurable because no selected model exists. Final chronological/symbol gates are INCONCLUSIVE; the blocker is the absent admissible inner threshold, not Portfolio coverage.','',
        '## Frozen model, training and state','',
        'Risk model `MSH_ENTRY_LONG_V2_1_V1_ANCHOR_D30_RIDGE_V1`: continuous D30=max(0,-strict30m MAE), weighted Linear Ridge λ1, unpenalized intercept, numpy.linalg.solve, float64, Python3.12 / NumPy2.3.5 / threads1. All four coefficients are penalized. Output max(0,raw); raw and contributions retained. Models are serialized and hash-checked on reload.','',
        'Input order: directionalMomentum3Pct, directionalPullback6Pct, momentum3Missing, pullback6Missing. Selector Score/Rank and v1 score/probabilities are excluded from the Risk matrix. Only the first two inputs are scaled; indicators remain0/1. Fold-only observed weighted median; no global/future/zero/time fill.','',
        'Eligible FIT anchors only receive w=1/(S×d_s×n_sd). All symbols have equal total weight, no manual exception. Labelability controls supervised loss only; every calibration anchor, including unknown labels, is causally scored. Original source statuses and both missing indicators are preserved.','',
        'v1 E[L]>=2 and original shadow state are unchanged. Risk rejects consume the original symbol-session eligibility. No later timestamp replacement, WAIT, re-entry, new v1-SKIP entry, delayed price or score sizing. Frozen277 identities remain intact.','',
        table(['Chronological inner','Fit labels','Momentum missing','Pullback missing','Both','Weighted medians M/P','Intercept','β M/P/mM/mP','Largest symbol weight'],[
            [f['name'],f['training']['eligibleRows'],*f['training']['missingCounts'],f['training']['bothMissingCount'],
             '/'.join(number(v) for v in f['medians']),number(f['intercept']),'/'.join(number(v) for v in f['coefficients']),pct(f['training']['largestSymbolWeightShare'])]
            for f in r['fitRecords'][:4]]),'',
        'All24 model SHAs, coefficients, medians, means/stds, missing counts, observed support, weight shares, objectives and residuals: [all-models-medians-weights.csv](all-models-medians-weights.csv). Exact FIT eligible/excluded IDs, per-event weights, symbols and sessions: run/models/*.json and run/fit-manifest.json.','',
        '## Baseline scope and unavailable selected challenger','']
    b76,b60=r['baselineFull76'],r['baselineGate60']
    pairs=[('ENTER','enterCount'),('ENTER/session','enterPerSession'),('Unique symbols','uniqueSymbols'),('Strict30m','strict30mCount'),
           ('Mean D30','meanD30'),('D30 ES95','ES95D30'),('Entry-count Symbol HHI','entrySymbolHHI')]
    lines.append(table(['Metric','v1 full76 inventory','v1 common60 outer scope','Selected v2.1'],[[label,number(b76[k]),number(b60[k]),'UNKNOWN / no selected OOF'] for label,k in pairs]+
        [[f'+{k} Precision',pct(b76['precision'][str(k)]['rate']),pct(b60['precision'][str(k)]['rate']),'UNKNOWN'] for k in (1,2,3,5)]+
        [[f'+{k} Anchor Preservation','100%','100%','UNKNOWN'] for k in (1,2,3,5)]+
        [[f'D30 {k}',number(b76['D30'][k]),number(b60['D30'][k]),'UNKNOWN'] for k in ['median','p90','p95']]+
        [[f'MAE {k}',number(b76['MAE'][k]),number(b60['MAE'][k]),'UNKNOWN'] for k in ['median','p05','worst']]+
        [[f'MAE<=-{k} count',b76['adverseCounts'][str(k)],b60['adverseCounts'][str(k)],'UNKNOWN'] for k in (2,5,10)]+
        [['MFE median',number(b76['MFE']['median']),number(b60['MFE']['median']),'UNKNOWN']]))
    lines+=['','96 full76 unknown labels:51 PROVIDER_GAP,25 LUNCH_BREAK,20 SESSION_END. Common60 has73 unknown labels. The saved strict30m six-bar low values agree on all181 anchors. No D30=0 substitution. No live-universe PIT claim: source3800 membership and frozen upstream are outcome-exposed; source field arrival clocks were not serialized.','',
        '## Risk decisions and winner cost','',
        'Diagnostics use nonexclusive labels: correct rejection = direct veto with observed D30>=5; false risk acceptance = ENTER with observed D30>=5; good acceptance = ENTER with MFE>=1 and D30<5. Rejected +1/+2/+3/+5 counts are separately retained even when the same path also has high adverse risk. Unknown and unsupported-input cases remain separate. These labels do not replace Gates.','',
        table(['Inner fold / τ2','Direct veto','Correct reject D30≥5','False rejects +1/+2/+3/+5','False accept D30≥5','Good accept','Censored anchors'],[
            [u['fold'],x['directRiskVeto'],x['correctRiskRejections'],'/'.join(str(x['falseRiskRejections'][str(k)]) for k in (1,2,3,5)),x['falseRiskAcceptances'],x['goodAcceptances'],x['censoredUnknown']]
            for u in r['chronological'] for x in [u['innerThresholdResults']['2']['attribution']['counts']]]),'',
        'Risk accepted/rejected D30 distributions and missingness strata are in each persisted unit. Complete per-anchor diagnostic records for all96 evaluations: risk-decisions-diagnostic.ndjson.gz. Overlapping calibration rows must not be treated as independent counts. No selected outer false-rejection/acceptance rate can be claimed.','',
        '## Secondary Portfolio and execution uncertainty','']
    p=r['portfolioBaseline'];conc=p['symbolConcentrationDiagnostic']
    lines.append(table(['Item','Frozen v1 common60 reference','Selected v2.1'],[
        ['Entry anchors / EXIT-resolvable',f"232 / {p['exitResolvableCount']}",'UNKNOWN'],
        ['Purchased / closed / unresolved',f"{p['trade']['accepted']} / {p['trade']['closed']} / {p['trade']['unresolved']}",'UNKNOWN'],
        ['Initial equity','1,000,000 JPY','1,000,000 JPY contract only'],
        ['Locked purchase notional',f"{p['lockedPurchaseNotionalJpy']:,.0f} JPY",'UNKNOWN'],
        ['Cash balance',f"{p['cashBalanceJpy']:,.3f} JPY",'UNKNOWN'],
        ['Final equity / Return / MaxDD','UNKNOWN: MISSING_BEFORE_EXIT','NOT_AVAILABLE: no selected OOF'],
        ['Closed-only PF / median JPY / win rate',f"{p['trade']['profitFactor']:.6f} / {p['trade']['closedPnlJpy']['median']:.2f} / {pct(p['trade']['winRate'])}",'UNKNOWN'],
        ['Closed-only worst / p05 JPY',f"{p['trade']['closedPnlJpy']['min']:.2f} / {p['trade']['closedPnlJpy']['p05']:.2f}",'UNKNOWN'],
        ['Capital utilization / idle cash','UNKNOWN with unpriced exposure','UNKNOWN'],
        ['Closed-only symbol positive / negative HHI',f"{conc['positive']['HHI']:.6f} / {conc['negative']['HHI']:.6f}",'UNKNOWN'],
        ['Closed-only effective positive / negative contributors',f"{conc['positive']['effectiveContributors']:.6f} / {conc['negative']['effectiveContributors']:.6f}",'UNKNOWN'],
        ['Closed-only profitable / losing symbols',f"{conc['profitableSymbols']} / {conc['losingSymbols']}",'UNKNOWN'],
        ['Top1 / Top3 positive symbol contributions',f"39360 +36,367.50 JPY; only1 net positive symbol",'UNKNOWN'],
        ['Top1 / Top3 symbol exclusion','Return and MaxDD still UNKNOWN; only1 positive symbol available','NOT_AVAILABLE']]))
    lines+=['','Locked position:89180, 2024-10-15 10:30 JST,47,900shares,335,300JPY purchase notional; first missing bar before EXIT at10:50 JST. No liquidation, carry-forward mark or invented cash release. Existing +23.05% complete-case173-trade reference is a different scope and is not substituted here.','',
        'Comparator unchanged: LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1, Equal/EQUAL_MAX3, initial1mJPY,100share lots,max10concurrent,budgetdivisor3,0.05% round-trip entry-notional cost, EXIT/cash release before new Entry. Score-free Equal matches original frozen277 weighting exactly. Engine and source hashes unchanged.','',
        'Execution MFE-versus-frozen-EXIT records are stored for all232 baseline outer anchors. 89180 low-price one-JPY movement uncertainty remains; no book/spread/depth/fill observation or new price/tick/symbol gate. No executable-quality claim.','',
        '## Gates, identity, integrity and STOP','',
        'All7 inner Primary conditions and5pp coverage gap were applied before selection. Final mean-D30/ES95/precision/retention/throughput, coverage, HHI≤1.1×baseline,3/4 chronological stability, direct-risk separation and3/5 symbol stability remain INCONCLUSIVE without selected OOF. Portfolio uncertainty neither fails nor relaxes Entry gates. No BORDERLINE reinterpretation.','',
        'The detailed contract definition of macro-symbol D30 is per-arm observed accepted-symbol means without imputation. The shorter applicationScopes phrase says fixed baseline symbols; the explicit metric definition is authoritative. No macro gate was reached in this run; this prose inconsistency has no effect on NONE or the verdict.','',
        table(['Identity','SHA'],[[k,v] for k,v in c['identity'].items() if 'SHA' in k or k=='selectorFreezeCommit']), '',
        table(['Implementation / evidence source','SHA-256'],[[p,sha(ROOT/p)] for p in
           ['predict/research/phase57_msh_entry_long_v2_1_d30.py','scripts/phase57_msh_entry_v2_1_evaluation.py','scripts/phase57_msh_entry_v2_1_development.py']]),'',
        'Contract deviations0; Risk feature changes0; Opportunity/Selector/EXIT/Allocation/ledger changes0; model tuning0; threshold additions0; Gate changes0; retries/retimed entries0. All existing100 source pins verify.','',
        'Fresh Validation0; Entry OOS0; EXIT OOS0; Prospective0; J-Quants0; Yahoo0; other price provider0; SHORT0. The Project runner and tests ran under inherited kernel network denial. Global Fresh budget195 remains untouched. All9 Safety flags false. main unmerged.','',
        'Evidence content seal: manifest.json + manifest.sha256 (includes source implementation/test/workflow pins). Prefit48 tests PASS; delivery tests additionally verify stored model hashes/weights, all96 gate calculations, saved predictions, exact anchor subsets, no outer fallback and locked-cash accounting without new Project fit/prediction. Final GitHub CI is checked at the published head.','',
        '**STOP.** Exact next action requires a separate instruction: blocker-resolution / v2.1 Root Cause Review using this saved evidence, followed only then by a separately frozen architecture decision. No threshold interpolation, Gate relaxation, v2.2 implementation, full76 candidate refit or Fresh/OOS in this work.','']
    (BASE/'README.md').write_text('\n'.join(lines))
    files=[p for p in BASE.rglob('*') if p.is_file() and p.name not in ['manifest.json','manifest.sha256','final-verification.json','final-verification.log']]
    sources=['predict/research/phase57_msh_entry_long_v2_1_d30.py','scripts/phase57_msh_entry_v2_1_development.py',
        'scripts/phase57_msh_entry_v2_1_evaluation.py','scripts/test_phase57_msh_entry_v2_1_runtime.py',
        'scripts/test_phase57_msh_entry_v2_1_evidence.py','scripts/report_phase57_msh_entry_v2_1_development.py',
        '.github/workflows/phase57-msh-entry-v2-1-development-integrity.yml']
    files += [ROOT/p for p in sources]
    manifest={'schemaVersion':1,'contractSHA':r['contractSHA'],'verdict':r['verdict'],'sourceHead':r['sourceHead'],
        'files':{str(p.relative_to(ROOT)):sha(p) for p in sorted(files)},
        'sealScope':'All immutable run/model/prediction/decision/gate/source/report artifacts; final verification receipt is downstream of this seal.'}
    (BASE/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    (BASE/'manifest.sha256').write_text(sha(BASE/'manifest.json')+'\n')
    print(json.dumps({'evidenceSHA':sha(BASE/'manifest.json'),'files':len(manifest['files']),'thresholdRows':len(thresholds)}))


if __name__=='__main__':main()
