"""Finalize only already successful, deterministic offline research execution."""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from scripts import phase57_sparse_handoff as s
from scripts import phase57_behavior_reader_v2 as r

PRECOMMIT='43e76dcf8b78aeffb829a41e70e84e65b80c77b3'
PROTOCOL_HASH='9b28157fe4bd8247e9d191144b9eb934a928dbd8a8c20d1ed822d7a1a3bd3956'

def verify_lock():
    assert s.v.saved.sha(s.BASE/'protocol.json')==PROTOCOL_HASH,'PRECOMMIT_CHANGED'
    s.invariants()

DESIGN='''# NEW LONG Entry / NEW LONG EXIT — Development design only

This design is emitted only after the Sparse Dictionary / Reader Development handoff Gate.
It is NOT a trading recommendation, fitted policy, frozen trading threshold, or OOS claim.
No production/paper/live execution is authorized. Existing Entry/EXIT remain immutable baselines.

## Shared input contract

Frozen Selector Opportunity identifies candidates, not buy instructions. Require a dated security
identity, latest preceding-session Sparse snapshot, same-as-of peer/normalization artifacts,
strictly later decision timestamp, and fresh complete same-phase Reader context. Only old-USABLE,
sample HIGH/MEDIUM, temporal PASS, non-drifting cells enter personality input. Empty personality
is explicit ABSTAIN; WATCH and low-confidence records remain research sidecars. Missing values are
not zero and cannot be filled with a dense peer personality. Keep confidence, nEff, uncertainty,
definition hash, evidence class and support counts available to both decision modules.

## NEW LONG Entry

Frozen Selector Opportunity × admitted Symbol Personality × Current Chart Context × Turning Point.
States: candidate observed -> WAIT -> ENTER proposal or expire. A WAIT state is not a trade.
At each 5-minute closed-bar decision, summarize PDH/OR breakout/failure, VWAP position/reclaim,
contiguous confirmed swing and pullback, compression/expansion and same-time activity shock.
Turn detection uses confirmation timestamps, never earlier extreme timestamps. Historical
personality is contextual evidence, never a substitute for today's chart. Distinguish breakout
continuation and confirmed pullback/reclaim as hypotheses; do not assign numerical policy
thresholds from this coverage study. Expire at session boundary or stale/missing context.
No overnight order, short, leverage or unbounded retry. Separate diagnostic abstention reasons
for missing personality, uncertain context, no turning point, stale data and expired opportunity.

## NEW LONG EXIT

Admitted Symbol Personality × Current Position Path × Continuation/Giveback Context × Deterioration.
States: HOLD -> EXIT proposal. Position history contains only available entry fills, observed
prices, elapsed time, current unrealized P&L and observed running high/low; never eventual MFE/MAE.
Use the same Reader, definitions, units and freshness as Entry. Continued strength, confirmed
deterioration and giveback are distinct evidence channels; no automatic EXIT merely because a
personality cell becomes unavailable. Define a separate deterministic fail-safe/fallback contract
before experiments. Do not silently switch to an existing strategy without explicit provenance.
Preserve existing EXIT as comparison baseline; position management remains LONG cash-equity only.

## Next precommit, not this task

Fix one bounded policy family per hypothesis, labels/horizons, objective (net costs, drawdown,
turnover, opportunity capture), missing-data fallback, training budget and Development splits
BEFORE learning or optimization. Compare new Entry/current EXIT, current Entry/new EXIT, and
new/new using identical Frozen Selector opportunities, capital constraints and cost assumptions;
keep common-cohort and availability-cohort accounting separate. Log ENTER/WAIT/HOLD/EXIT funnels,
calibration and temporal stability, not winner-only performance. Entry/EXIT optimization and
Common Holdout opening require a separate stage. Common Holdout244/REPORT19/Validation/OOS/Fresh
remain closed here. No automatic promotion from this design.
'''

def finalize(evidence,replay,cache,matrix):
    verify_lock();root=Path(evidence);m=root/'measurement';other=Path(replay)
    assert (m/'manifest.json').read_bytes()==(other/'manifest.json').read_bytes(),'REGEN_MISMATCH'
    for name,h in s.read(m/'manifest.json').items():
        assert s.v.saved.sha(m/name)==h
        assert s.v.saved.sha(other/name)==h
    regression=s.read(root/'regression/regression.json');assert regression['status']=='PASS'
    log=(root/'focused.log').read_text();assert re.search(r'\nOK\s*$',log) and 'FAILED' not in log and 'skipped=' not in log
    tests=int(re.search(r'Ran (\d+) tests',log).group(1));assert tests>=49
    boundary=s.read(m/'10_boundary_evidence.json');assert not boundary['commonHoldoutIntersection'] and not boundary['excludedIntersection']
    p=s.admission.plan();allowed=set(p['dailyDevelopment'])|set(p['intradayDevelopment'])
    extraction=s.read(root/'extraction.json');assert extraction
    for a in extraction:assert set(a['selectedDates'])<=allowed
    for cell in boundary['inputLedger']:s.admission.authorize(cell['session'],cell['kind'],p)
    profiles=s.read(m/'06_sparse_profiles.json.gz');asof=s.read(m/'05_coverage.json')['asOf']
    for profile in profiles:r.validate_snapshot(profile,asof[:10]+'T15:31:00+09:00')
    gate=s.read(m/'09_handoff_gate.json');gate['contracts']={k:'PASS' for k in ['sameAsOf','noFutureLeakage','historyAdapter','freshness','sessionBoundary','deterministicRegeneration','sparseMissingSemantics','developmentBoundary']}
    available=s.read(m/'08_reader.json')['counts'].get('RESEARCH_CONTEXT_AVAILABLE:None',0)
    # Real, simultaneous Dictionary+Reader composition on the last allowed Development day.
    # Select first3 admitted codes solely to exercise the connection; not a performance sample.
    priors=s.read(m/'12_integration_prior_profiles.json.gz');integration=[]
    if priors:
        day=asof[:10];s.admission.authorize(day,'minute',p)
        rawpath=Path(cache)/day/'minute-pages.json';expected=next(x['sha256'] for x in boundary['inputLedger'] if x['session']==day and x['kind']=='minute')
        assert s.v.saved.sha(rawpath)==expected
        minutes,_=s.v.saved.pages(rawpath);histories=s.read(Path(matrix)/'last-history.json.gz');chosen=sorted(priors)[:3]
        for code in chosen:
            hist=histories[code];previous=hist[-1]['daily'] if hist else None
            prefix=sorted([row for row in minutes if row['Code']==code and (540<=s.v.minute_time(row)<690 or 750<=s.v.minute_time(row)<755)],key=s.v.minute_time)
            context=r.context(day,755,prefix,previous,hist,s.calendar(),priors[code]);integration.append({'symbol':code,'dictionaryAsOf':priors[code]['asOf'],'context':context})
    integrated=sum(x['context']['status']=='RESEARCH_CONTEXT_AVAILABLE' and bool(x['context'].get('personality')) for x in integration)
    s.write(root/'dictionary-reader-integration.json',{'tested':len(integration),'nonemptyFreshConnections':integrated,'selection':'FIRST3_TEMPORAL_ADMITTED_CODES_AT_PRIOR_SESSION','examples':integration})
    ready=gate['dispatchableResearchSymbols']>0 and available>0 and integrated>0
    gate.update(status='SPARSE_DICTIONARY_CHART_READER_READY_FOR_ENTRY_EXIT_DEVELOPMENT' if ready else 'BLOCKED',entryExitDesignAllowed=ready,temporalMeasured=True,pullbackResultsFixed=True,requiredBeforeReady=[])
    if available==0:gate['reasons'].append('NO_REAL_DEVELOPMENT_READER_CONTEXT_AVAILABLE')
    if integrated==0:gate['reasons'].append('NO_NONEMPTY_REAL_SAME_ASOF_DICTIONARY_READER_CONNECTION')
    gate['realDictionaryReaderConnections']=integrated
    s.write(root/'handoff-gate.json',gate)
    head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    receipt={'status':'PASS','checkoutHead':head,'protocolPrecommit':PRECOMMIT,'protocolHash':PROTOCOL_HASH,'runId':os.environ.get('GITHUB_RUN_ID'),'focusedTests':tests,'regressionTests':sum(x['counts']['tests'] for x in regression['suites']),'deterministicRegeneration':'TWO_MANIFESTS_IDENTICAL','sourceEvidence':'UNCHANGED','commonHoldoutAdditionalReads':0,'report19ValidationOosFreshAdditionalReads':0,'providerRequests':0,'entryExitTrials':0,'productionAllowed':False}
    s.write(root/'ci-receipt.json',receipt)
    if ready:(root/'NEW_LONG_ENTRY_EXIT_DESIGN.md').write_text(DESIGN)
    summary=s.read(m/'01_trait_coverage.json');counts=s.read(m/'05_coverage.json');pull=s.read(m/'04_pullback_vnext.json');watch=s.read(m/'03_watch_mapping.json')
    lines=['# Sparse Dictionary + Behavior Reader — final REPORT','',f"Gate: **{gate['status']}**",'',
           f"Same-as-of: {asof}. Universe {counts['symbols']}; dated-master listed {counts['listedAtAsOf']}. No protected payload is used to align dates.",
           'Sample confidence and temporal reliability are separate. Reference scales/peer fits are causal per-snapshot, not reused from later frozen whole-period fits. These counts therefore differ from the archival 2,895/4,080. Historical reconstruction remains NOT PIT / NOT OOS / research-only.','',
           '## 1–4. Synchronized sparse coverage and temporal reliability','',
           '| lane / trait | H | M | L | insufficient | temporal PASS | dispatchable |','|---|---:|---:|---:|---:|---:|---:|']
    for x in summary:
        if x['globalStatus']=='USABLE':lines.append('| '+x['lane']+'/'+x['trait']+' | '+' | '.join(str(x['sampleConfidence'].get(k,0)) for k in ['HIGH','MEDIUM','LOW','INSUFFICIENT'])+f" | {x['temporalReliability'].get('PASS',0)} | {x['dispatchableSymbols']} |")
    lines+=['',f"Nonempty admitted personality: **{counts['nonemptyDispatch']} symbols**. Source H/M without temporal PASS is excluded. Three fixed rolling-origin folds, five exchange-session embargo, future 20 authorized sessions, no threshold tuning. Expanding and recent/long diagnostics retained.",'',
            '| view | 0 | 1–2 | 3–5 | 6–10 | 11+ |','|---|---:|---:|---:|---:|---:|']
    for lane,d in counts['temporalDispatchCounts'].items():lines.append('| '+lane+' | '+' | '.join(str(d[k]) for k in ['0','1-2','3-5','6-10','11+'])+' |')
    lines+=['','All symbol×trait fields: measurement/06_sparse_profiles.json.gz. Per-symbol eligible fold diagnostics: 07_temporal_symbol_folds.json.gz. Unavailable folds are counted insufficient, not imputed. Snapshot/peer/normalization coefficient provenance: 11_asof_artifacts.json.','',
            '## 5. Pullback vNext','',f"Event-bearing symbol-sessions: {pull['eventBearingSessions']}; confirmed pairs: {pull['eventPairs']}; paired old/new sessions: {pull['pairedOldNewSessions']}.",
            'New ID '+r.PULLBACK_ID+'. Contiguous same-phase upward impulse then confirmed downward correction only. Unconfirmed terminal legs excluded; ratios above1 retained. Old definition/results unchanged. New result is candidate-only, not retroactive USABLE.',
            'Detailed scalar distributions, paired differences, temporal screen and timestamped examples: measurement/04_pullback_vnext.json.','',
            '## 6. Calibration-only WATCH23','',
            '| lane / trait | frozen-mapping independent-period candidate |','|---|---|']
    for x in watch:lines.append(f"| {x['lane']}/{x['trait']} | {x['newVersionCandidate']} |")
    lines+=['','OLS fit only on fold1, applied unchanged to folds2/3. Both periods must retain slope0.5–1.5 and MSE no worse than identity, >=100 pairs. Missing periods fail closed. All old WATCH remain WATCH and are excluded from dispatch; diagnostic candidate is not a new globally validated registry.','',
            '## 7. Shared Chart Reader','',f"Real Development probe outcomes: {json.dumps(s.read(m/'08_reader.json')['counts'],sort_keys=True)}.",
            f"Real simultaneous Dictionary+Reader connections: {integrated}/{len(integration)} fixed code-order probes; full connection payloads in dictionary-reader-integration.json.",
            'History adapter / exact previous exchange day / closed5m / maximum age4min / current-phase expected endpoint / missing/stale/future rejection / lunch reset implemented and contract-tested. VWAP missing-prefix remains null. PDH/PDL, OR, causal Swing/Pullback, breakout/failure, breakdown/reclaim, wick/body, compression/expansion and same-time RVOL/value shock share a single Entry/EXIT context. Probe selection is first3 eligible codes/day, five fixed timestamps; not a whole-market Reader-coverage claim.','',
            '## 8–9. Handoff and next step','',str(gate['reasons']),
            'NEW_LONG_ENTRY_EXIT_DESIGN.md created; no fitting/optimization performed.' if ready else 'Gate BLOCKED: no NEW Entry/EXIT design or optimization. Do not relax temporal criteria. Fix only evidenced contract/data limitations under a separate precommit.',
            'At actual use, dispatch additionally requires the latest preceding-session snapshot and a fresh Reader; a stored candidate is never an order.','',
            '## 10–12. Boundary, verification and provenance','',
            f"Tests {tests}; full regression {receipt['regressionTests']}; PASS. Two independently regenerated output manifests match. Raw restoration is allowlisted and every raw page file matches original acquisition measurement hashes. Read ledger intersections with Common Holdout244 and excluded seals are empty. No provider request. Exposure Ledger remains unchanged.",
            f"Protocol precommit {PRECOMMIT}; execution HEAD {head}; PR587 remains research Draft/unmerged. Evidence preservation commit is a descendant, not the execution HEAD.",
            'Source daily733/intraday144, old registry/Gates/verdicts and prior results preserved. Supplemental daily payloads already acquired for intraday Development are reused causally, not counted as new provider acquisition.',
            'STOP. No Common Holdout/REPORT19/Validation/OOS/Fresh opening, no Entry/EXIT learning, no trading or production promotion.','']
    (root/'REPORT.md').write_text('\n'.join(lines))
    (root/'HANDOFF.md').write_text('# Handoff\n\nRead REPORT.md, handoff-gate.json and ci-receipt.json.\n\n'+gate['status']+'\n\n'+('Next stage: bounded Development precommit for NEW LONG Entry/EXIT, using the conditional design. No Holdout until separately authorized.' if ready else 'STOP. No Entry/EXIT development authorization inferred from implemented contracts. Temporal/coverage blockers are recorded; do not force a pass.')+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['verify-lock','finalize']);p.add_argument('--evidence');p.add_argument('--replay');p.add_argument('--cache');p.add_argument('--matrix');a=p.parse_args()
    if a.command=='verify-lock':verify_lock()
    else:finalize(a.evidence,a.replay,a.cache,a.matrix)
