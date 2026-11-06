"""Freeze one Development-only Path Anatomy cycle before reading path outcomes."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
PRIOR = ROOT / 'docs/evidence/phase57-profit-target-extension/cycle-20260929-01'
BASE = '9a0b6749b8e1835fb553c0a593a88c7044ff9648'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name: str, value: dict) -> None:
    path = OUT / name
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True,
                               separators=(',', ':'), allow_nan=False) + '\n')


def main() -> None:
    old = json.loads((PRIOR / 'SOURCE_MANIFEST.json').read_text())
    pins = {}
    for key in ('rawPath', 'phaseAAccounting', 'integrationZip', 'executionCode',
                'integrationPrecommit', 'capitalScores'):
        source = old['pins'][key]
        path = ROOT / source['path']
        if sha(path) != source['sha256'] or path.stat().st_size != source['bytes']:
            raise ValueError('SOURCE_DRIFT:' + key)
        pins[key] = source
    allow = PRIOR / 'ENTRY_ALLOWLIST.json'
    original = json.loads(allow.read_text())
    if {a: len(original[a]) for a in ('IM', 'R1')} != {'IM': 819, 'R1': 795}:
        raise ValueError('ALLOWLIST_SCOPE')
    pins['entryAllowlist'] = {'path': str(allow.relative_to(ROOT)),
                              'bytes': allow.stat().st_size, 'sha256': sha(allow)}
    at = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds')
    save('START_AUDIT.json', {
        'savedJst': at, 'basisHead': BASE, 'branch': 'research/phase57-long-only-cash-equity',
        'draftPr': 587, 'branchAndPrReadOnlyChecked': True, 'prOpenDraft': True,
        'basisHeadMatchesOperator': True, 'commitPrWorkflowRuns': 0,
        'previousCycle': 'phase57-profit-target-extension/cycle-20260929-01',
        'previousStatus': 'RESULT_SAVED_INVALID_MAIN_POSTPROCESS_INDEPENDENT_ROWS_PASS',
        'previousBudgetRemainingMain': 0, 'previousBudgetRemainingIndependent': 0,
        'duplicatePathAnatomyCycleAtStart': False,
        'priorDevelopmentOutcomeExposure': True,
        'newPathOutcomesInspectedAtFreeze': False,
    })
    save('SOURCE_MANIFEST.json', {
        'basisHead': BASE, 'pins': pins,
        'frozenSessions': 24, 'allEntryIds': {'IM': 819, 'R1': 795},
        'fundedIds': {'IM': 79, 'R1': 32},
        'entryWorlds': {'IM': 'IMMEDIATE', 'R1': 'ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF'},
        'entryIdentity': '(arm, entryId=session|symbol|entryMinute)',
        'sourceHashVerifiedBeforeAnatomy': True,
        'sourceLimitations': ['historical provider publication knownAt is not proven',
                              'minute no-trade/missing/halt semantics not fully proven'],
    })
    save('ANATOMY_PRECOMMIT.json', {
        'schema': 'phase57-exit-path-anatomy-v1', 'savedJst': at,
        'basisHead': BASE, 'sourceManifestSha256': sha(OUT / 'SOURCE_MANIFEST.json'),
        'population': 'frozen ALL Entry IM and R1 separately; funded subset inside ALL',
        'end': 'same-session continuous bar starts 09:00..11:29,12:30..15:24 plus exact 15:30 auction',
        'entryBarOwned': True, 'auction': 'endpoint-stamped single-price row, reported separately from 1m Close',
        'priceValidation': '7 numeric finite fields, positive OHLC, Low<=Open/Close<=High; duplicate minutes invalid',
        'knownMasks': {
            'priceKnown': 'finite positive effective Entry plus at least one valid post-Entry bar',
            'continuousPathKnown': 'all scheduled continuous minutes from Entry through 15:24 valid',
            'pathKnown': 'continuousPathKnown and exact valid single-price 15:30 auction',
            'stateKnown': 'exact per-checkpoint saved State/Signal snapshot with barEnd and knownAt proven',
            'unknown': 'not pathKnown; may have confirmed observed hits, but never a certified miss',
        },
        'primaryAnalysisMask': 'pathKnown, with observed positive hits on incomplete paths separately flagged; no 0 imputation',
        'milestonesPct': [0.5, 1, 2, 3, 5, 7, 10],
        'higherPairs': {'1': [2, 3, 5, 10], '2': [3, 5, 10],
                        '3': [5, 7, 10], '5': [7, 10], '7': [10]},
        'initialWeaknessPct': [-0.5, -1],
        'candidateFloorsPct': {'1': 0, '2': 1.5, '3': 2.5},
        'return': '100*(price/effective paid Entry-1), percent; giveback difference in percentage points',
        'netMark': '100*(100*exact finalized Close - 100*effective paid Entry*(1+0.0005))/(100*effective paid Entry); hypothetical mark, not executable PnL',
        'highOpportunity': 'observed Entry-owned High including auction; not a realizable sale',
        'closeOpportunity': 'finalized continuous 1m Close, auction final mark separate',
        'firstPassage': 'High and Close first valid scheduled bar; active time counts scheduled continuous minutes, lunch excluded',
        'partialPath': 'positive observed event is a confirmed touch, but first-passage time is left-censored if any prior missing; a missing event is UNKNOWN',
        'intrabar': 'High vs Low order unknown in same bar. Strict post-anchor bars used for ordered floor-before-winner; same-bar cases separate AMBIGUOUS.',
        'floorTouch': 'Low<=candidate floor (inclusive), with exact equality and strict Low<floor also reported',
        'floorCrossClassification': 'after first High anchor and before first strictly later higher High: DEFINITE_CROSS only when all intervening bars known and floor first occurs in an earlier bar; SAME_BAR_AMBIGUOUS when first floor and higher High occur in one bar; NO_CROSS when higher High first; missing path UNKNOWN',
        'winner': 'later higher High strictly after anchor; simultaneous anchor-bar higher High is not a later winner; separate simultaneous count',
        'pullback': 'minimum Low and maximum drawdown from prior completed-bar running High on bars strictly after anchor and before first higher target bar; target bar overlap separate; anchor itself excluded; censored at terminal if no target',
        'givebackFraction': '100*maxGivebackPp / maximum prior Entry-to-High percent when positive',
        'duration': 'peak bar to pretarget trough in active continuous minutes; first later Close>trough-bar Close is recovery onset; former/new High touch measured from trough across remaining fixed horizon; null if absent',
        'weakness': 'first Low<=-0.5/-1 before first +1 High on different bars; same bar AMBIGUOUS. Later recovery milestones require strictly later bar; same bar separately ambiguous.',
        'stateDiagnostic': {
            'checkpoint': 'first finalized Close in a strictly later continuous bar after first +1 High that is <=+0.5% return, if full path known',
            'outcome': 'later +5 High in a strictly subsequent bar vs certified no later +5 through fixed endpoint; simultaneous checkpoint bar excluded',
            'primitives': ['consecutiveDownCloses','lowerHighCount3','lowerLowCount3','drawdownFromPriorPeakPp','last3CloseSlopePp','last5ClosePathEfficiency','reboundToPriorDrawdownRatio','barsSinceNewHigh'],
            'comparison': 'descriptive medians by outcome and fixed 0.5pp bins of prior peak and current close; no classifier, fitted weights, or threshold choice',
            'insufficient': 'STATE_INCREMENT_NOT_DEMONSTRATED if no stable interpretable within-bin evidence; no claim State generally worthless',
        },
        'quantiles': [0.10, 0.25, 0.50, 0.75, 0.90],
        'quantileInterpolation': 'linear, numpy default; worst is max adverse giveback/min return as appropriate',
        'concentration': 'distinct sessions, symbols, top session and symbol share; nested samples not independent',
        'independentAudit': 'second script with separate parser and bar-order logic; exact N/cross counts and 1e-9 numeric quantiles; one call only',
        'figures': ['entry-high', 'milestone-giveback', 'minimum-before-later-winner',
                    'weakness-recovery', 'floor-cross', 'representative-state-paths'],
        'budget': {'path_anatomy_main': 1, 'independent_anatomy_recalculation': 1,
                   'new_estimator_fits': 0, 'calibration_fits': 0, 'new_policy_replays': 0,
                   'integrated_capital_replays': 0, 'new_exit_candidate_implementations': 0,
                   'threshold_optimization': 0, 'new_provider_requests': 0,
                   'protected_openings': 0, 'orders': 0, 'main_merges': 0},
        'selection': 'DESIGN_ONLY; no floor, initial stop, State threshold, or feature weight selected',
    })
    save('EXPOSURE_LEDGER.json', {
        'savedJst': at, 'partitions': {'Outcome-exposed Development 24 sessions': 'E2',
                                    'Protected/Fresh/Validation/OOS/Prospective': 'UNOPENED'},
        'priorCyclesSeen': ['Phase A', 'Phase A+', 'Profit Target diagnostic'],
        'newPathAnatomyMainConsumed': 0, 'independentRecalculationConsumed': 0,
        'historicalDevelopmentCannotBecomeFresh': True,
    })
    print('FROZEN', sha(OUT / 'ANATOMY_PRECOMMIT.json'), at)


if __name__ == '__main__':
    main()
