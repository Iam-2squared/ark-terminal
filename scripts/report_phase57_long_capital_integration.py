"""Publish immutable, compressed replay evidence and bounded Development report."""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path

from scripts.phase57_long_capital_integration import CONTRACT, OUT, digest


def fmt(x, digits=2):
    return 'UNKNOWN' if x is None else f'{x:,.{digits}f}' if isinstance(x, (int, float)) else str(x)


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(fmt(x) for x in row)+' |' for row in rows])


def publish(source, out=OUT):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    raw = (Path(source)/'measurement.json').read_bytes()
    data = json.loads(raw)
    primary = data['reports']['FULL277']
    diagnostic = data['reports']['EXPOSED_COMMON173_DIAGNOSTIC']
    fixed = data['reports']['EXPOSED_COMMON173_FIXED_REFERENCE']
    equal, rank = diagnostic['EQUAL_MAX3'], diagnostic['LONG_RANK_MAX3']
    stripped = copy.deepcopy(data)
    for scope, value in stripped['reports'].items():
        for result in ([value] if scope.endswith('FIXED_REFERENCE') else value.values()):
            for key in ['equityCurve', 'closedTrades', 'decisions']:
                del result[key]
    outputs = {'measurement.json.gz': gzip.compress(raw, mtime=0),
               'summary.json': (json.dumps(stripped, indent=2, allow_nan=False)+'\n').encode(),
               'causal-entry-envelopes.json': (Path(source)/'causal-entry-envelopes.json').read_bytes()}
    lineage = {
        'legacyMaxN': 'predict/portfolio/phase57-p25-lane-c-portfolio-simulator.js; cash-collateral LONG+SHORT research; no silent reuse',
        'adaptiveV2': 'predict/portfolio/phase57-p25-adaptive-allocation-v2.js; confidence/probability/selection quality schema incompatible with frozen E[L]; not measured',
        'latestCapitalBranch': 'research/phase57-capital-allocation-v3-phase-b-integrated',
        'latestCapitalHead': '84b296102b85ab2909385a8f3ee7ef336c9b6129',
        'latestCandidate': 'V3_B_RISK × MAX_3, maximumConcurrentPositions10; MAX_5 conservative sub, MAX_10 legacy',
        'riskDisposition': 'Requires exact7 pre-entry completed CLOSEs; current post-entry artifact has no such window. Not measured. No inference from later bars, no silent equal fallback.',
        'longOnlySessionAllocation': 'predict/long-only/phase57-long-only-session-allocation-v3.json is DATA SPLITTING, not capital allocation',
        'reusedExactFiles': {p: digest(p) for p in ['scripts/lib/phase57-capital-allocation-v3-entrytime.mjs', 'predict/research/phase57-capital-allocation-v3-entrytime-contract.json']},
        'reusedFunction': 'allocateV3 V3_0_EQUAL and V3_A_RANK arithmetic only; old Entry builder, risk arm and v4/v5 adapters never invoked',
        'newLongCandidate': 'LONG_RANK_MAX3 uses frozen E[L] ordinal ranks. This changes the score meaning explicitly; NOT unchanged legacy V3_A_RANK evidence.',
        'parameterSearch': 'Three arms once, one inherited MAX_3 budget, no grid and no post-result rule changes',
    }
    outputs['lineage-audit.json'] = (json.dumps(lineage, indent=2)+'\n').encode()
    attributions = {
        'primaryBottleneck': 'DATA_COVERAGE_AND_REFERENCE_FILL_SEMANTICS',
        'full277': {'firstUnpriced': primary['EQUAL_MAX3']['firstUnknownValuation'],
                    'firstPositionCapitalLockedJpy': primary['EQUAL_MAX3']['lockedPurchaseNotionalJpy'],
                    'equitySizingRejected': primary['EQUAL_MAX3']['trade']['rejectionReasons'].get('CURRENT_EQUITY_UNKNOWN', 0)},
        'secondaryOnly': {
            'rankMinusEqualFinalJpy': rank['finalEquityJpy']-equal['finalEquityJpy'],
            'selectedExitMinusFixedFinalJpy': equal['finalEquityJpy']-fixed['finalEquityJpy'],
            'selectedExitMinusFixedMaxDDPctPoints': equal['maxDrawdownPct']-fixed['maxDrawdownPct'],
            'equalCashBlocked': equal['trade']['rejectionReasons'].get('INSUFFICIENT_CASH', 0),
            'equalLotBlocked': equal['trade']['rejectionReasons'].get('TARGET_BELOW_LOT', 0),
            'equalConcurrencyBlocked': equal['trade']['rejectionReasons'].get('MAX_CONCURRENT_POSITIONS', 0),
            'largestSymbol': max(equal['concentration']['groupPnlJpy']['symbol'], key=equal['concentration']['groupPnlJpy']['symbol'].get),
            'largestSymbolPnlJpy': max(equal['concentration']['groupPnlJpy']['symbol'].values()),
            'netMinusLargestSymbolContributionJpy': equal['closedTradeNetPnlJpy']-max(equal['concentration']['groupPnlJpy']['symbol'].values()),
            'contributionRemovalIsNotCounterfactualReplay': True,
        },
        'selectorEntry': 'Frozen; cannot infer their causal marginal value from this already-selected, outcome-exposed subset. Need same-date integrated reference.',
        'exit': 'Some reference-level improvement passes into equal-allocation portfolio; median trade weakness and tail/concentration remain. Not proven biggest bottleneck; no EXIT v2 started.',
        'allocation': 'New rank arm underperforms equal on this diagnostic return and DD; no evidence to prefer complexity. Equal remains comparison reference, not validated/final winner.',
        'utilization': 'Equal mean deployment about8.26%, but peak97.35%; low average does not justify leverage or blindly larger sizing. Sparse frozen stream and shorter holding are distinct from concurrency blocking.',
        'existingArkFairComparison': 'Ledger/envelope semantics reusable, but actual fair comparison not run; legacy streams are different dates/Entry/EXIT. Full same-window data, fill and missing contracts required.',
        'nextResearchQuestion': 'Audit existing archived Development minute checkpoints for missing/no-trade classification and exact pre-entry7 closes; freeze executable fill/latency/liquidity and unresolved valuation rules separately. Never fill gaps or retune EXIT to force completion.',
    }
    outputs['bottleneck-attribution.json'] = (json.dumps(attributions, indent=2)+'\n').encode()
    report = [
        '# Phase57 LONG-only Capital / Full Integration — Development Evidence',
        '**CAPITAL_INTEGRATION_IMPLEMENTED_FULL277_MEASUREMENT_BLOCKED**. The event-time ledger and paired Allocation replay are implemented. Full277 final equity is UNKNOWN, not zero. No Allocation Development Final, Validation PASS, OOS PASS or Production Ready claim. EXIT is unchanged.',
        'Source head `ba0ccdb2aea7e5fc9fee817c0bd95f09427108f8`; branch `research/phase57-long-only-cash-equity`, PR #587. Historical76 sessions / Frozen277 ENTER only. All data are Development, IN-SAMPLE, outcome-exposed. No provider requests, Fresh consumption or OOS access; Fresh195 remains untouched. This work does not reopen or consume Validation20.',
        '## Lineage and frozen comparison',
        'Latest existing allocation is **V3_B_RISK × MAX_3**, not Adaptive v2. The latest freeze is on `84b296102b85ab2909385a8f3ee7ef336c9b6129`, separate from the LONG-only branch. Its old MSH probability/features and risk window cannot silently be substituted with LONG E[L]. Exact V3 equal/rank arithmetic and contract files are imported verbatim; the old Entry builder, old EXIT adapters and risk scorer are not run. `phase57-long-only-session-allocation-v3.json` allocates data sessions, not money. See lineage-audit.json.',
        'Three fixed arms: ONE_LOT_REFERENCE (one100-share lot per accepted Entry), EQUAL_MAX3 (equal simultaneous budgets), LONG_RANK_MAX3 (new LONG E[L] ordinal-rank adaptation). Budget divisor3 and maximum10 positions come from the latest lineage; no divisor search. V3_B_RISK remains INPUT_NOT_AVAILABLE on this post-entry-only bundle, not an equal fallback.',
        'Initial cash ¥1,000,000;100-share lots; LONG/cash only. Same Entry identities/timestamps/prices, frozen LONG EXIT, costs, event ordering and missing rules in every primary arm. The sole extra Fixed12 arm uses Equal/MAX3 on the same pre-existing173 diagnostic identities. It is an EXIT transmission reference, not a reselection.',
        '## Accounting and causal semantics',
        'Completed-bar observation → unchanged EXIT state update → reference sale/cash release → simultaneous Entry sizing snapshot → symbol/eventId-ordered cash-constrained purchases → exact observed MTM. Timestamp formats are normalized before ordering. Entry allocator accepts only eventId/timestamp/symbol/frozen score, never EXIT results/MFE/MAE. Future bars reach the EXIT one completed bar at a time. Target and cash quantities are separately rounded down to100 shares. No unused-budget redistribution.',
        'Cash cannot go negative; open positions cannot exceed10; quantity is in100-share lots. Cash + purchase notional of open positions = initial cash + ledger-realized PnL. Fees are0.025% of Entry notional at each side, exactly0.05% total, preserving the frozen EXIT reference-cost convention. This is not a broker-specific fee model. Unrealized gains never become available cash. Closed-trade net and realized ledger balance are reconciled separately to avoid double-charging Entry cost.',
        'Missing expected bar before EXIT permanently censors that position; quantity and purchase capital remain locked. Later bars cannot resurrect/price it or invent a sale. Current-equity sizing then rejects CURRENT_EQUITY_UNKNOWN. One-lot sizing may still spend actual remaining cash; it eventually accumulates unresolved positions. Calendar-known zero-remaining-bar Entries are rejected without inventing positions. Unknown holdings are accounting liabilities, not a decision to carry an overnight trade.',
        '**Fill limitation:** Entry decision-price and EXIT same-completed-close prices are research reference marks, not guaranteed fills. No spread, latency, queue, participation/volume constraint or slippage is proved. DD is sampled observed-close portfolio MTM, not intrabar worst-case DD. Thin/low-price names and large share quantities are especially exposed. No forward fill, interpolation, future substitution or auction repair.',
        '## Primary: all277 ENTER, no future-completeness filtering',
        table(['Arm','Candidates','Accepted','Closed','Unresolved','Cash JPY','Locked purchase JPY','Final equity'],
              [[a,277,r['trade']['accepted'],r['trade']['closed'],r['trade']['unresolved'],r['cashBalanceJpy'],r['lockedPurchaseNotionalJpy'],r['finalEquityJpy']] for a,r in primary.items()]),
        f"First unknown valuation: **{primary['EQUAL_MAX3']['firstUnknownValuation']}**. Symbol17570 entered13:00 on2024-09-17, with missing slot3 before its frozen EXIT. Equal/rank accepted it causally and retain ¥{fmt(primary['EQUAL_MAX3']['lockedPurchaseNotionalJpy'])} purchase capital. Thereafter256 equity-based Entry attempts cannot be sized;20 have no remaining regular bar. They are not silently deleted from the277. Full return, full MaxDD and full utilization remain NULL. Closed-only one-lot PF is not full portfolio PF.",
        'Source frozen EXIT availability by reason: `'+json.dumps(data['sourcePathAvailability'], sort_keys=True)+'`. A missing expected bucket may represent no trading or missing observations; that distinction has not been repaired or assumed here.',
        table(['Arm','Rejected reason','Count'], [[a,k,n] for a,r in primary.items() for k,n in r['trade']['rejectionReasons'].items()]),
        '## Secondary ONLY: pre-existing173 common identities',
        '**Not the result of the full277 strategy.** This previously outcome-exposed complete-case subset excludes104 identities using future-path availability inherited from EXIT Development. It is fixed before Allocation replay but not a deployable filter. All arms use the exact same173 and all76 session dates, including empty sessions. No new session replacement or exclusion is performed. Informative missingness can materially bias results.',
        table(['Arm','Final JPY','Return %','MTM MaxDD %','MaxDD JPY','Closed','PF','Win rate %'],
              [[a,r['finalEquityJpy'],r['totalReturnPct'],r['maxDrawdownPct'],r['maxDrawdownJpy'],r['trade']['closed'],r['trade']['profitFactor'],100*r['trade']['winRate']] for a,r in diagnostic.items()]),
        table(['Arm','Mean/median trade JPY','Worst session %','Session p05 %','Loss streak','Largest loss JPY','Net <=-10%'],
              [[a,fmt(r['trade']['closedPnlJpy']['mean'])+' / '+fmt(r['trade']['closedPnlJpy']['median']),r['worstSession']['returnPct'],r['sessionReturn']['p05'],r['maxConsecutiveLosingSessions'],r['trade']['largestLossJpy'],r['trade']['tailMinus10Count']] for a,r in diagnostic.items()]),
        table(['Arm','Avg utilization %','Peak %','Idle cash %','Turnover JPY','Cash releases','Same-time recycled Entries','Max/avg positions'],
              [[a,100*r['capital']['averageUtilization'],100*r['capital']['peakUtilization'],100*r['capital']['idleCashRatio'],r['capital']['grossTurnoverJpy'],r['capital']['cashReleaseCount'],r['capital']['sameTimestampRecyclingEntries'],str(r['capital']['maxConcurrent'])+' / '+fmt(r['capital']['averageConcurrent'])] for a,r in diagnostic.items()]),
        'Utilization is trading-time weighted over all76 sessions, including flat time; lunch and overnight are excluded. Mean low deployment and near-full peak deployment are both visible. Cash-release count does not mean every released yen was subsequently redeployed. Same-timestamp recycling is counted separately.',
        table(['Arm','Positive trade Top1/3/5 shares','Positive symbol Top1/3/5 shares','Symbol notional HHI','Position-size HHI'],
              [[a,' / '.join(fmt(r['concentration']['positiveTradeProfitShares']['top'+str(k)],4) for k in [1,3,5]),' / '.join(fmt(r['concentration']['symbolPositiveProfitShares']['top'+str(k)],4) for k in [1,3,5]),r['concentration']['symbolNotionalShares']['hhi'],r['concentration']['positionNotionalShares']['hhi']] for a,r in diagnostic.items()]),
        'Top shares use positive-profit sums, never a misleading net denominator. Full symbol/session PnL, HHI, all session returns, exit-reason performance, rejected opportunity outcomes and every cash/position decision are in summary.json and measurement.json.gz.',
        f"Equal/MAX3 net ¥{fmt(equal['closedTradeNetPnlJpy'])} includes symbol89180 contribution ¥{fmt(equal['concentration']['groupPnlJpy']['symbol']['89180'])}. Subtracting that accounting contribution gives ¥{fmt(attributions['secondaryOnly']['netMinusLargestSymbolContributionJpy'])}. This is NOT a leave-symbol-out cash replay and is not used to make a symbol exception. The positive result is materially concentrated.",
        '## Fixed EXIT transmission reference — same Equal/MAX3 and173',
        table(['EXIT','Final JPY','Return %','PF','MaxDD %','Avg utilization %','Accepted'],
              [[label,r['finalEquityJpy'],r['totalReturnPct'],r['trade']['profitFactor'],r['maxDrawdownPct'],100*r['capital']['averageUtilization'],r['trade']['accepted']] for label,r in [('FIXED12',fixed),('FROZEN_LONG_EXIT',equal)]]),
        f"Frozen LONG EXIT improves this reference final balance by ¥{fmt(equal['finalEquityJpy']-fixed['finalEquityJpy'])}. Lower holding time lowers average deployment. This is a Management × Allocation interaction, not proof that EXIT is solved or the causal largest bottleneck. EXIT code/rules were not changed.",
        '## Bottleneck attribution and decision',
        '1. **Data coverage first:** all277 portfolio value is unidentifiable under the unchanged missing rules. Do not present173 returns as277 or delete unresolved cash exposure.\n2. **Execution/price semantics:** no executable fill or volume capacity proof; sparse and low-price paths can dominate.\n3. **Concentration/tail:** secondary Equal MaxDD20.17%; one-symbol contribution exceeds aggregate net.\n4. **Cash utilization:**8.26% mean but97.35% peak; increasing nominal sizing blindly is unsupported.\n5. **Concurrency/lot:** Equal has0 position-limit rejects,6 below-lot and1 cash reject; concurrency10 is not the main observed173 constraint. Rejected outcomes are evaluator-only.\n6. **Allocation:** rank is lower-return/higher-DD than simple equal in this limited sample; no reason to prefer complexity.\n7. **Selector/Entry/EXIT:** frozen and not marginally identifiable here; no retuning or EXIT v2 initiation.',
        '**No Capital Allocation Development Final is selected.** Keep Equal/MAX3 as the comparison reference, not a proven winner. The next concrete task is to audit existing archived Development minute checkpoints for missing/no-trade versus cache gaps, and recover an exact causal7-close risk window if available without any new provider/Fresh/OOS access. A separately frozen executable-fill/latency/liquidity and unresolved-position contract is needed before truthful full portfolio claims. Do not invent missing prices to force completion.',
        'Existing-Ark fair-comparison architecture can reuse the sanitized Entry envelopes, frozen EXIT callbacks and common ledger. Actual Existing-Ark same-window replay has NOT been performed. Current legacy evidence uses different periods/Entry/EXIT and is not a fair performance comparator. Validation20 remains protected, not consumed for this Development tuning.',
        '## Evidence / verification',
        'Contract and candidate family were written locally before the first Allocation replay; they are published with results, not separately timestamped remote preregistration. No parameter sweep, post-result policy change, independent Claude review or winner promotion. Engineering fixes/tests do not alter frozen upstream. Fresh/OOS access0; Safety all9 false; no main merge.',
        'The17 existing EXIT/upstream tests are preserved, alongside new cash-ledger/causality/reproduction tests. Final publishing-head CI is recorded by GitHub, not assumed by this report. Compressed evidence expands byte-for-byte to the original measurement; publication manifest records its raw/compressed hashes.',
    ]
    outputs['report.md'] = ('\n\n'.join(report)+'\n').encode()
    outputs['handoff.md'] = ('''# LONG Capital / Portfolio next-stage handoff

Status: CAPITAL_INTEGRATION_IMPLEMENTED_FULL277_MEASUREMENT_BLOCKED.
Frozen Selector / MSH-Entry LONG threshold2 /277 identities / LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1 unchanged.
No Allocation final selected. Equal/MAX3 remains comparison reference; new rank is not promoted.

Implemented: causal100-share cash ledger, same-time EXIT release before Entry, fees exactly once, ten-position limit, three fixed arms, unresolved liabilities, complete cash traces and observed MTM. Primary277 is unpriceable; secondary173 is outcome-exposed diagnostics only, NOT full-system performance.

Next: inspect existing archived Development minute checkpoints for missing/no-trade semantics and exact7 pre-entry closes; no provider request/Fresh/OOS authorization is implied. Freeze a separate realistic fill/latency/liquidity contract without changing frozen policy decisions. Never invent a price, exit, cash release or zero loss. No additional allocation grid or EXIT retuning before resolving these blockers.

Reproduce under the network guard:
`ARK_TEST_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 python3 scripts/offline/kernel_exec.py python3 -m unittest scripts/test_phase57_long_capital_integration.py scripts/test_phase57_long_exit_continuation.py scripts/test_phase57_msh_entry_upstream_freeze.py`

Read report.md, summary.json, bottleneck-attribution.json and lineage-audit.json. Full event ledger is measurement.json.gz. Full277 final equity/DD/return are NULL by design; do not replace them with173 figures. Existing-Ark fair comparison not yet run. Validation20/Fresh195 protected. All9 safety flags false; no main merge.
''').encode()
    for name, content in outputs.items():
        path = out/name
        assert not path.exists(), 'IMMUTABLE_OUTPUT_EXISTS'
        path.write_bytes(content)
    code_paths = ['scripts/phase57_long_capital_integration.py', 'scripts/phase57_long_capital_weights.mjs',
                  'scripts/report_phase57_long_capital_integration.py', 'scripts/test_phase57_long_capital_integration.py',
                  '.github/workflows/phase57-long-capital-integration.yml', str(CONTRACT)]
    manifest = {'status': data['status'], 'sourceHead': json.loads(CONTRACT.read_text())['startHead'],
                'rawMeasurementSHA256': hashlib.sha256(raw).hexdigest(),
                'artifacts': {name: hashlib.sha256(value).hexdigest() for name,value in outputs.items()},
                'codePins': {path: digest(path) for path in code_paths},
                'upstreamPins': data['upstreamPins'], 'safety': data['safety'],
                'primary277FinalEquityKnown': False, 'secondary173IsFullPortfolioEvidence': False,
                'allocationFinalSelected': False, 'freshConsumed': 0, 'oosAccess': 0}
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'status': data['status'], 'publishedFiles': len(outputs)+1,
                      'compressedBytes': len(outputs['measurement.json.gz'])}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--output', default=str(OUT))
    args = parser.parse_args()
    publish(args.source, args.output)
