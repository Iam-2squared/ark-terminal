"""Report saved screen evidence only. No fitting, prediction or alternate thresholds."""
import csv
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'docs/evidence/phase57-entry-v2-2-fast-fail'


def main():
    r = json.loads((BASE/'result.json').read_text())
    c = json.loads((ROOT/'predict/research/phase57-entry-v2-2-fast-fail-protocol-v1.json').read_text())
    models = json.loads(gzip.decompress((BASE/'models.json.gz').read_bytes()))
    failed = [g['name'] for g in r['gates'] if g['status'] == 'FAIL']
    def csv_out(name, fields, rows):
        with (BASE/name).open('x', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
            w.writeheader(); w.writerows(rows)
    csv_out('screen-gates.csv', ['name','value','operator','limit','status'], r['gates'])
    rows = []
    for u in r['units']:
        a = next(x['artifact'] for x in models if x['unit'] == u['name'])
        rows.append({'unit':u['name'], 'trainingRows':u['trainInputRows'],
            'trainingLabelable':u['trainLabelableRows'], 'evaluationRows':u['evaluationRows'],
            'evaluationLabelable':u['metrics']['targetEvaluable'],
            'spearman':u['metrics']['spearman'], 'mseSkill':u['metrics']['mseSkill'],
            'medianMomentum':a['medians'][0], 'medianPullback':a['medians'][1],
            'missingMomentum':a['training']['missingCounts'][0],
            'missingPullback':a['training']['missingCounts'][1],
            'trainingSymbols':len(a['training']['symbols']),
            'largestSymbolWeight':a['training']['largestSymbolWeight'],
            'modelSHA':a['artifactSHA']})
    csv_out('units.csv', list(rows[0]), rows)
    decision = {'verdict':r['verdict'], 'failedGates':failed,
        'scope':'Kill this signed-mean-reference-return / five-input Ridge / economic-breakeven hypothesis; not every possible Entry Quality target.',
        'structuralFinding':'Small positive average-return prediction does not produce an adverse-path-safe, winner-preserving selection at the preregistered cut.',
        'notEstablished':['Nonlinear model advantage','Profitability of an executable Entry policy','All Net Entry Quality targets impossible'],
        'nextArchitectureCount':1,
        'nextArchitectureProposal':'ONE minimal joint-success classifier: probability of a positive frozen-EXIT net reference result AND an independently specified acceptable adverse path. Predefine the path budget from the objective, not this result; use one low-capacity model. This replaces the signed-mean objective rather than changing its cut or adding a D30 veto.',
        'proposalEvidenceLimit':'Predictability is unproven. Requires a separate minimal preregistered screen; no numeric target boundary chosen here.',
        'implementedNextArchitecture':False, 'newTargetTrialsAfterKill':0,
        'noRescue':['No threshold changes','No extra feature','No model upgrade','No excluded fold','No symbol rule','No Fresh/OOS'],
        'nextAction':'STOP. Do not run full Development or freeze a candidate from this screen.'}
    (BASE/'decision.json').write_text(json.dumps(decision,ensure_ascii=False,indent=2)+'\n')
    b = r['coexistence']; all_, pos = b['allScored'], b['positive']
    pp = lambda x: 'UNKNOWN' if x is None else f'{100*x:.4f}%'
    f = lambda x: 'UNKNOWN' if x is None else f'{x:.6f}'
    lines = [
        '# Phase57 Entry v2.2 FAST-FAIL — ' + r['verdict'], '',
        'Historical / Development / outcome-exposed only. Protocol was published in commit '
        '`ab6fa75fa778b2790165781e7c7749cb596d4741` before Project target computation, fit or prediction. '
        'No full Development or new Portfolio replay was performed.', '',
        '**Stop this hypothesis.** A positive-return score has a small descriptive signal, but the '
        'fixed breakeven screen worsens adverse paths and loses too many frozen v1 winners. '
        'No new thresholds, targets, inputs or model settings were tried after this finding.', '',
        '| Precommitted requirement | Observed | Result |', '|---|---:|---|',
        f'| Chronological positive rank direction ≥3/4 | 3/4 | PASS |',
        f'| Held-symbol positive rank direction ≥3/5 | 3/5 | PASS |',
        f'| Chronological MSE improvement over train-only constant >0 | {pp(r["pooled"]["chronological"]["mseSkill"])} | PASS, small |',
        f'| Held-symbol MSE improvement >0 | {pp(r["pooled"]["symbolDisjointLastWindow"]["mseSkill"])} | PASS, small |',
        f'| Positive-band mean D30 no worse | {all_["D30"]["mean"]:.4f}% → {pos["D30"]["mean"]:.4f}% (+{100*(pos["D30"]["mean"]/all_["D30"]["mean"]-1):.2f}%) | FAIL |',
        f'| Retain ≥90% of v1 +3 winners | 67/82 = {pp(b["v1WinnerRetention"]["3"]["retention"])} | FAIL |',
        f'| Retain ≥90% of v1 +5 winners | 36/47 = {pp(b["v1WinnerRetention"]["5"]["retention"])} | FAIL |',
        f'| Retain ≥80% of v1 anchor count in score band | 206/232 = {pp(b["v1AnchorScoreBandThroughput"])} | PASS |', '',
        'These are **score-band diagnostics**, not executable ENTER counts or cash Portfolio returns. '
        'D30 comparison in this table uses all held candidates versus the positive-score band; '
        'winner-retention denominators use exact frozen v1 anchors on the same held timestamps. '
        'The two denominators must not be conflated.', '',
        '## Hypothesis and scope', '',
        'One signed continuous target: frozen LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1 net reference return, '
        '`Q = 100*(exitReference/decisionPrice - 1) - 0.05`. This rewards retained upside and penalizes '
        'realized-reference loss under a fixed downstream exit. It does not itself penalize an adverse '
        'excursion followed by recovery; D30 is therefore a separate evaluation check. Reference closes '
        'are not verified executable fills.', '',
        'Exact inputs: Selector Ridge Score, Momentum3, Pullback6, Momentum missing, Pullback missing. '
        'Selector score supplies upside context to a signed-quality target; this is not labelled an '
        'independent risk model. No symbol, price, time, liquidity, rank, future label, new feature or '
        'execution proxy enters the prediction. Training-fold weighted medians and weighted raw '
        'mean/std only; unscaled missing indicators. Weighted Ridge λ=1, numpy.linalg.solve, signed '
        'linear output, no clipping, weight 1/(S*d_s*n_sd), unpenalized intercept.', '',
        'The only diagnostic cut is predicted Q>0 (net economic breakeven). No cut was selected by '
        'performance. No Entry state, timing replacement, sizing or Portfolio implementation was built. '
        'Prior D30 threshold-veto failures remain immutable evidence.', '',
        '## Bounded evaluation', '',
        'Four expanding chronological windows: 16→15, 31→15, 46→15 and 61→15 sessions. Five '
        'fixed-hash held-symbol groups use only the last chronological evaluation window. '
        'All train/eval session and symbol-session intersections are zero; held-symbol intersections '
        'are zero in the five group tests. All label endpoints precede the next held block. '
        'No alternative split, inner threshold calibration or extra fit was used.', '',
        '| Unit | Training / target available | Held / target available | Spearman | MSE skill |',
        '|---|---:|---:|---:|---:|']
    for row in rows:
        lines.append(f'| {row["unit"]} | {row["trainingRows"]}/{row["trainingLabelable"]} | '
                     f'{row["evaluationRows"]}/{row["evaluationLabelable"]} | {f(row["spearman"])} | {pp(row["mseSkill"])} |')
    lines += ['',
        'Exactly 9/9 Project fits succeeded and 3,750 numerical predictions were saved: 3,000 '
        'chronological records plus 750 separate last-window held-symbol records. Duplicate IDs '
        'within each scope=0. The 750 held-symbol records overlap the chronological scope by design '
        'and must not be counted as new observations. The first16 sessions are training warm-up only.', '',
        'MSE skill compares each trained model with its training-fold symbol-weighted constant mean; '
        'evaluation error is symbol/session/event balanced within a unit and units are pooled equally. '
        'Spearman is event-level with average tied ranks. Repeated observations are not independent '
        'statistical evidence; no significance or p-value claim is made.', '',
        '## Winner and adverse-path coexistence', '',
        '| Held chronological score band | All scores | Q prediction >0 |', '|---|---:|---:|',
        f'| Candidate events | {all_["events"]} | {pos["events"]} |',
        f'| Target-evaluable events | {all_["Q"]["n"]} | {pos["Q"]["n"]} |',
        f'| Mean frozen-exit net reference return | {f(all_["Q"]["mean"])}% | {f(pos["Q"]["mean"])}% |',
        f'| Reference-return PF (not Portfolio PF) | {f(all_["referenceReturnPF"])} | {f(pos["referenceReturnPF"])} |',
        f'| Strict30m evaluable | {all_["D30"]["n"]} | {pos["D30"]["n"]} |',
        f'| Mean D30 | {f(all_["D30"]["mean"])}% | {f(pos["D30"]["mean"])}% |',
        f'| D30 ES95 | {f(all_["D30"]["upperES95"])}% | {f(pos["D30"]["upperES95"])}% |',
        f'| D30 ≥10 count / strict30m N | 18/1451 | 11/492 |',
        f'| Median MFE | {f(all_["MFE"]["median"])}% | {f(pos["MFE"]["median"])}% |', '',
        'The positive-score band increases upside opportunity but also selects more adverse paths. '
        'Its mean net reference return is still approximately zero after the frozen cost. Among v1 '
        'anchors alone, mean D30 moves 2.677622%→2.558126% (4.46% reduction), while +3 and +5 '
        'winner retention falls below90%. This supporting subset does not replace the preregistered '
        'Full Replacement screen or its gates.', '',
        'Top-two reference-contribution symbol removal (89180, 67400; ranked by repeated-event net '
        'return sums, **not Portfolio contribution**) leaves Spearman '
        f'{f(r["top2RemovalDiagnostic"]["metrics"]["spearman"])} and MSE skill '
        f'{pp(r["top2RemovalDiagnostic"]["metrics"]["mseSkill"])}. Direction remains slightly positive; '
        'this experiment does not establish that two-symbol dependency is the primary cause of failure. '
        'No symbol was excluded from fitting or runtime scoring.', '',
        '## Coverage, PIT and Portfolio limits', '',
        'Shared universe: 76 sessions, 2024-09-17–2025-01-09, 760 decision timestamps, 3,800 Top5 '
        'events. Frozen v1: 353 raw qualified, 277 state-constrained anchors, 181 strict30m labelable '
        'and96 unlabelable. The new fixed-exit target is observable for1,897/3,800;1,903 are unknown '
        '(1,743 missing before EXIT;160 no remaining regular bar). Strict D30 is observable for1,828 '
        'of3,800. Censored outcomes are excluded from training loss/metrics only and remain NULL '
        'in the ledger. All3,750 held candidate records were scored before evaluator-side label joins.', '',
        'Positive-band target coverage differs by2.7235pp and D30 coverage by4.7078pp from all '
        'chronological scores, both inside the precommitted5pp screen. This does not prove missingness '
        'is random. Results are conditional on available labels. No fill, interpolation, substitution '
        'or missing-as-zero was used.', '',
        'Existing feature code enforces completed-bar availableAt<=decision. Saved rows do not '
        'serialize every raw arrival clock. The inherited3800 membership and Frozen Selector/v1 '
        'training are outcome-exposed; this is not a clean full-stack OOS experiment. The new model '
        'alone uses chronological or held-symbol train/eval isolation.', '',
        'Portfolio evidence is reused: full-stream unresolved position1, locked cash335,300 JPY. '
        'Final Equity/MaxDD remain UNKNOWN. The prior+23.05% belongs to173 complete-case trades. '
        'No new Portfolio replay, synthetic liquidation, cash release, engine change, or execution '
        'quality filter was introduced. Low-price/tick/spread/depth/fill uncertainty remains diagnostic.', '',
        '## Decision and one next proposal', '',
        decision['scope'], '', decision['nextArchitectureProposal'], '',
        decision['proposalEvidenceLimit'], '',
        '**STOP.** No full Development contract or candidate freeze is warranted for this screen. '
        'The next proposal is not implemented or evaluated. Do not rescue the failed mean-return '
        'score through a different cutoff, feature expansion, stronger model or Fresh data.', '',
        '## Integrity and artifacts', '',
        '- Branch: `research/phase57-long-only-cash-equity`; PR#587 remains Draft/unmerged.',
        '- Starting head: `e9c0f64674bd759bae369085c179522136992898`; latest-main-at-start: '
        '`c48be22db7deef286b0bb5dc1951964431145908`.',
        '- Protocol SHA: `'+r['protocolSHA']+'`.',
        '- Source pins:107 verified, including Selector/v1/EXIT/Allocation/ledger and both failure lineages.',
        '- Prefit:15 synthetic/contract/leakage tests PASS. Postfit:20 tests PASS using saved evidence; '
        'no Project refit/prediction during verification.',
        '- Fits9, predictions3750, target candidates1, models1, threshold searches0, retuning0, '
        'Fresh/OOS/Prospective/provider requests0, SHORT0. All nine safety flags false.',
        '- Global budget SHA: `'+c['identity']['globalBudgetSHA']+'`; Fresh195 unchanged.',
        '- Full exact metrics/gates/per-symbol bands: `result.json`; per-unit summary: `units.csv`; '
        'all gates: `screen-gates.csv`.',
        '- Exact fitted coefficients, weighted medians/scales, training IDs/weight audits/model SHAs: '
        '`models.json.gz`; causal predictions and separate evaluation labels: `predictions.json.gz`.',
        '- All3800 target identities/censor reasons/frozen EXIT results: `target-ledger.json.gz`.',
        '- Precommit source pins, prefit receipt/log, execution log and manifest preserve run order. '
        'The final commit is the commit containing this evidence manifest; verify its exact-head CI '
        'through GitHub, not a prior commit status.', '',
        '### Frozen identity references', '',
        '| Identity | SHA |', '|---|---|']
    for key, value in c['identity'].items():
        lines.append(f'| {key} | `{value}` |')
    (BASE/'README.md').write_text('\n'.join(lines)+'\n')


if __name__ == '__main__':
    main()
