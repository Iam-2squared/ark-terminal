"""Render saved Development evidence; no replay, predictions or provider access."""
import hashlib,json
from pathlib import Path

B=Path('docs/evidence/phase57-long-exit-continuation-v1')
def load(n):return json.loads((B/n).read_text())
def fmt(x):return 'N/A' if x is None else (f'{x:.4f}' if isinstance(x,float) else str(x))
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |',*['| '+' | '.join(fmt(x) for x in r)+' |' for r in rows]])+'\n'
def ratio(d):return f"{d['count']}/{d['denominator']} ({fmt(d['ratePct'])}%)"
def main():
 m=load('measurement.json');f=load('development-final.json');d=load('path-diagnostic.json');t=load('winner-timing-supplement.json');c=load('contract.json');arms=list(m['metrics']);modes=m['metrics'];selected=f['selectedMode'];s=modes[selected];sha=hashlib.sha256((B/'development-final.json').read_bytes()).hexdigest()
 sections=['# Phase57 LONG EXIT Development Final — 2026-09-16 JST',
 'Selected: **LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1**. Status: **LONG_EXIT_DEVELOPMENT_FINAL_SELECTED_NOT_VALIDATED**. One research handoff candidate, not an independent superiority finding or trading approval.',
 'Repo `Iam-2squared/ark-terminal`, branch `research/phase57-long-only-cash-equity`, PR #587. Start head `3a42db5b1ca000308bd91b3dbda9ac455bdfa956`; main checked `b7801ce2c13772cbc3f5b51506819c119fe868ea`. This report belongs to its publishing commit; final-head CI is recorded by GitHub checks.',
 'All 76 sessions (2024-09-17–2025-01-09) are direct Entry Development, IN-SAMPLE, outcome-exposed Historical reuse. Frozen 277 ENTER identities are retained. Common complete-case comparison N=173; 104 remain censored/unpaired, without replacement. Selected standalone availability is 192, which is **not** used against a 173-trade baseline. Informative missingness/complete-case selection may limit generalization.',
 '## Design and causal execution semantics',
 'The prior v5 remains V5_LONG_MEASUREMENT_BLOCKED: its unavailable historical v4 continuation has not been fabricated. This is explicitly new LONG Development research inheriting BAR5 Defensive/Reclaim and replacing continuation. No v3/v4 performance replay or new analog pool was run.',
 table(['State/input','Rule'],list(f['rules'].items())),
 'The first completed trading bar uses CLOSE >= Entry reference as non-adverse, including exactly flat. Negative enters DEFENSIVE; reclaim by BAR5 inclusive resets the decline streak. Continuation exits after two consecutive strictly lower completed CLOSEs; equality or increase resets the streak. Both initial non-adverse and reclaimed cohorts use this same rule. A pre-existing Fixed12/calendar cap bounds every candidate. No symbol/sector exceptions.',
 'Inputs are observed completed CLOSE and past state only. Future HIGH/LOW/MFE/MAE are evaluator-only. HIGH/LOW order within a bar is UNKNOWN_INTRABAR_ORDER and never inferred. Decisions at a completed CLOSE are valued at that same reference CLOSE, **not a proven executable fill**. Latency, subsequent tradable price and slippage remain integration work. Round-trip cost = 0.05 percentage point for all arms.',
 'Five-minute expected trading slots skip lunch; clock holding time includes lunch. No overnight carry. Calendar-known shortened sessions cap before the regular-session boundary. Missing expected bars censor before an exit; missing bars after an already emitted exit do not change that exit. No forward-fill/interpolation/provider substitution. The inherited post-November 15:25/auction gap is not silently repaired. Session-End is diagnostic only on 41 complete paths, not a main comparison arm.',
 '## Candidate family and selection',
 'Before the candidate replay, contract.json fixed only three research candidates: BAR5 + inherited Fixed12 continuation; BAR5 + half of observed positive completed-CLOSE peak giveback; BAR5 + two consecutive lower CLOSEs. The half ratio and two-confirmation count are explicit simple design assumptions, not calibrated optimums. They were not swept or changed after the replay. Contract and outputs are published together; their generation order is local, not a separately timestamped remote preregistration.',
 table(['Component','Predeclared ordinal-rank weight'],list(c['selectionWeights'].items())),
 'Lower weighted rank loss wins, ties by predeclared simplicity order. Net sum is not the selection objective. This is a Development design choice with subjective weights, not statistical proof.',
 table(['Candidate','Weighted rank loss'],list(m['selection']['weightedRankLoss'].items())),
 '## Post-entry path diagnostic',
 table(['Cohort','All 277','Paired N'],[(g,d[g]['n'],next(iter(m['cohortSplit'][g].values()))['n'] if g in m['cohortSplit'] else 0) for g in d if g!='ALL']),
 'A includes 135 strictly positive and 54 flat first bars. B=33 reclaim, C=25 no reclaim, D=30 incomplete. First-bar observation uses the next trading bar: 250 observed; strict wall-clock +5m availability below is a different definition.',
 table(['Wall-clock horizon','Available N','CLOSE median %','MFE median %','MAE median %','Giveback median pp'],[(h,x['available']['count'],x['close']['median'],x['mfe']['median'],x['mae']['median'],x['giveback']['median']) for h,x in d['ALL']['horizons'].items()]),
 'Horizon denominators differ; these are not paired duration improvements. path-diagnostic-ledger.json preserves per-ENTER returns, observed running extrema/update times, first-positive/reclaim/threshold-hit times and missing status.',
 table(['Cohort','30m N','30m CLOSE median','30m MFE median','60m N','60m CLOSE median','60m MFE median'],[(g,d[g]['horizons']['30']['close']['n'],d[g]['horizons']['30']['close']['median'],d[g]['horizons']['30']['mfe']['median'],d[g]['horizons']['60']['close']['n'],d[g]['horizons']['60']['close']['median'],d[g]['horizons']['60']['mfe']['median']) for g in d if g not in ['ALL','D_PATH_INCOMPLETE']]),
 'Initial non-adverse paths have more upside than reclaimed paths; no-reclaim paths have materially negative subsequent CLOSE medians. These observations justify separating Defensive from Continuation, but not automatic early liquidation of every adverse trade or assuming recovery from deep losses.',
 '## Winner timing (post-selection diagnostic)',
 'This supplemental table was generated after selection, and was not a selection input. Available MFE means the inherited Fixed12/calendar window, not all-day maximum or attainable profit. Longer-bar rows drop calendar-shortened cases; denominators are explicit.',
 table(['Bar','Available N','Mean observed/full-window MFE fraction','+3 first hit by bar','+5 first hit by bar'],[(k,x['n'],x['meanObservedMfeFractionOfFixedWindow']['mean'],ratio(x['firstHitByBar']['3']),ratio(x['firstHitByBar']['5'])) for k,x in t['mfeFractionsAndHitsByBar'].items()]),
 'The bar6 snapshot sees about 91% of the reference-window MFE on average, but misses some +3/+5 first hits. This does not establish bar6 as an optimal exit. The chosen runtime has no new bar6 timeout. Giveback after the hindsight MFE bar is saved in winner-timing-supplement.json as evaluation only.',
 '## Paired performance — N=173 in every column',
 'Returns below are reference-price/cost-adjusted trade percentages. Net/gross sums and drawdown proxies are percentage-point sums over unweighted trades, **not portfolio return or portfolio mark-to-market drawdown**.',
 table(['Arm','Net sum pp','Gross sum pp','Mean %','Median %','Win rate','PF','Worst %','p05 %','<=-10% N','DD entry-order proxy pp'],[(a,x['netSumPctPoints'],x['grossSumPctPoints'],x['net']['mean'],x['net']['median'],ratio(x['winRate']),x['profitFactor'],x['net']['min'],x['net']['p05'],x['tailMinus10'],x['ddCommonEntryOrderProxyPctPoints']) for a,x in modes.items()]),
 table(['Arm','Mean loss %','Median loss %','Mean holding bars','Median bars','Mean clock minutes','Pre-exit MAE median %','Pre-exit MAE p05 %','MFE capture median','Giveback mean pp','Giveback median pp'],[(a,x['loss']['mean'],x['loss']['median'],x['holdingBars']['mean'],x['holdingBars']['median'],x['holdingClockMinutes']['mean'],x['preExitMae']['median'],x['preExitMae']['p05'],x['mfeCaptureGross']['median'],x['givebackPctPoints']['mean'],x['givebackPctPoints']['median']) for a,x in modes.items()]),
 'MFE capture = gross reference exit return / common available MFE. MFE<=0 is undefined (8 cases; capture N=165), not zero-filled. Full distributions and exit-order DD proxies are in measurement.json. This ratio can be large negative when positive MFE is tiny.',
 '## Winner preservation',
 table(['Arm','Level','Available winner N','Final net positive','Final net >= level','Exit before first HIGH touch','Winner mean net %'],[(a,k,z['available'],ratio(z['positiveFinal']),ratio(z['realizedAtLeastLevel']),ratio(z['prematureBeforeFirstTouch']),z['finalNet']['mean']) for a,x in modes.items() for k,z in x['winnerLevels'].items()]),
 'Positive final net is a weak preservation measure and is separated from realizing the full opportunity level. Same-bar touches are not called premature because intrabar order is unknown.',
 '## Dynamic state and cohort performance',
 table(['Arm','DEFENSIVE','RECOVERED','BAR5 failure','Recovered mean net %','Recovered positive','Failed recovery N','No-reclaim mean net %','False defensive exit later Fixed positive'],[(a,x['dynamic']['defensive'],x['dynamic']['recovered'],x['dynamic']['bar5Failure'],x['dynamic']['recoveredNet']['mean'],ratio(x['dynamic']['recoveredWinRate']),x['dynamic']['failedRecovery'],x['dynamic']['noReclaimNet']['mean'],x['dynamic']['falseDefensiveExitLaterPositiveFixedClose']) for a,x in modes.items()]),
 table(['Cohort','Arm','N','Mean net %','PF'],[(g,a,x['n'],x['net']['mean'],x['profitFactor']) for g,aa in m['cohortSplit'].items() for a,x in aa.items() if a in ['FIXED12',selected]]),
 'False recovery here means recovered then negative final net; false defensive exit means BAR5 exit followed by a positive Fixed reference close. These are retrospective diagnostics, not decision inputs.',
 table(['Arm','Available-window MAE<=-10 cohort N','Cohort mean final net %','Cohort worst net %','Saved net winners vs Fixed','Lost net winners vs Fixed'],[(a,x['pathMaeMinus10CohortFinalNet']['n'],x['pathMaeMinus10CohortFinalNet']['mean'],x['pathMaeMinus10CohortFinalNet']['min'],x['savedNetWinnersVsFixed'],x['lostNetWinnersVsFixed']) for a,x in modes.items()]),
 'The available-window deep-adverse cohort has 17 cases and differs from strict30m. All 10 previously identified strict30m MAE<=-10% cases are retained in the paired sample; no deep-tail case was removed from that prior cohort.',
 '## Concentration and fragility',
 table(['Arm','Positive-profit Top1 share','Top3','Top5','Positive improvement Top1 share','Top3','Top5','Net delta pp','Net delta removing best improvement pp'],[(a,*[x['concentration']['positiveProfitTop1Top3Top5'][str(k)] for k in [1,3,5]],*[x['positiveImprovementTopShares'][str(k)] for k in [1,3,5]],x['netDeltaVsFixedPctPoints'],x['largestPositiveDeltaRemoved']) for a,x in modes.items()]),
 'Shares are fractions of summed positive trade profits or summed positive paired improvements, not shares of net profit. Full symbol/session concentration is saved for every arm.',
 table(['Selected arm group','Identity','Trades','Net sum pp','Absolute return share'],[(g,z['identity'],z['trades'],z['netSumPctPoints'],z['absoluteReturnShare']) for g,rows in s['concentration']['grouped'].items() for z in rows[:5]]),
 '## Decision and remaining risk',
 'Freeze the two-lower-CLOSE policy as the single Development Final because it balances fewer severe final losses, better PF/p05, retained positive +3/+5 winners and simple causal continuation. The half-peak candidate reduced p05 but damaged aggregate performance and winner preservation; the Fixed continuation control had slightly higher net sum but poorer worst-tail/PF trade-offs. No additional parameters were tried.',
 '\n'.join('- '+x for x in f['knownLimitations']),
 'The +5.4118pp total net improvement becomes -4.8685pp after removing its largest improvement trade. Consequently improvement robustness is not established. The selected policy is a research foundation, not a claim that downside risk is solved. Net median remains -0.05%, MFE capture median is zero, and median giveback worsens. Recovered winners remain a weak cohort.',
 '## Integrity and handoff',
 'Frozen Selector/Entry/277 identity and all pinned upstream artifacts verified unchanged. Entry prediction/refit=0; new analog=0; SHORT evaluation=0; provider requests=0; Fresh consumption=0; OOS access=0. Global Fresh budget stays195. All nine safety flags are false. Initial targeted regression:17 PASS under kernel network denial; final publishing-head CI must be checked separately. No Claude independent review was performed.',
 f'Development Final SHA-256: `{sha}`. Exact identities and all hashes are in development-final.json. See [capital-handoff.md](capital-handoff.md). Next: Capital Allocation **research integration** of this one frozen Development policy, with explicit executable-fill/latency, cash constraints, overlapping positions, missing-position accounting and portfolio MTM semantics before claiming portfolio performance. No automatic promotion, main merge or Fresh/OOS evaluation.',
 '## Frozen upstream file hashes',table(['Artifact','SHA-256'],list(f['upstreamPins'].items()))]
 (B/'report.md').write_text('\n\n'.join(sections).rstrip()+'\n')
 handoff=f'''# Capital Allocation research handoff

One selected policy: `{f['policyId']}`. Status `{f['status']}`.
Manifest: [development-final.json](development-final.json); SHA-256 `{sha}`.
Evidence and limits: [report.md](report.md). Historical Development/IN-SAMPLE only; Fresh Validation and OOS remain PENDING.

Use `predict/long-only/phase57_long_exit_development_final.py` as the single research interface. It has no provider, order, broker or v4 dependency. Import by file path, call `new_position(remaining_regular_slots, direction="LONG", cash_equity_only=True)`, then `on_completed_bar(state, bar)` in contiguous expected trading-slot order. `remaining_regular_slots` is calendar-known, not the count of later observed bars. Supply `slot`, `missing`, `c`, `end`, `minutes`; `c=100*(completedClose/unchangedEntryReference-1)`. `end` is the completed bar timestamp and `minutes` is elapsed wall-clock time. Lunch is skipped in trading slots, not wall-clock time.

Return status is `HOLD_RESEARCH_STATE`, `EXIT_REFERENCE`, or `CENSORED`. An emitted EXIT_REFERENCE is final; never append another exit or reuse a closed symbol-session. All same-bar reference fills remain research marks, not broker execution. For truthful executable portfolio simulation, freeze a separate causal fill/latency contract first without silently altering this policy's decisions. Missing bars before exit produce CENSORED; Capital must not discard an unresolved position or assume zero loss, free cash or an invented exit.

Entry stays Threshold2.0, frozen model/scaler/features/ENTER-SKIP; Selector stays Top5 with existing cadence. Entry Historical=BORDERLINE, Fresh Validation=PENDING. Frozen277 identity SHA `72224ac9fd073f7da45c488aaf8ca999752b466e715837c21440e7dd93970236`.

Rules: BAR1 non-adverse including zero -> continuation; adverse -> DEFENSIVE; CLOSE reclaim by BAR5 inclusive -> RECOVERED and reset decline count; no reclaim -> BAR5 close reference exit. Continuation: two consecutive strictly lower completed CLOSEs; equality/rise resets. Maximum12 expected trading bars or shorter calendar cap. Cost0.05pp. Do not substitute session-end, BAR6, analogs or another policy.

Primary evidence173 common pairs from277; standalone selected exit references192. The unpaired104 are not additional evidence of comparative improvement. All76 sessions are exposed; budget195 is untouched. No SHORT/margin/leverage. No allocation optimization or portfolio claims were performed here.

Residual risks: worst reference net -23.5794%; median -0.05%; recovered mean negative; removing best improvement reverses net improvement; same-close fills unproven; post-Nov auction coverage unresolved; closed-trade DD proxies are not portfolio MTM drawdown. Preserve these limits in every downstream report.

Next authorized research topic: integrate the one policy with cash-only capital, overlapping-position/lot/cost accounting and explicit missing/fill handling. Independent Entry/EXIT Validation/OOS remain separate confirmation gates. Do not tune Entry or this EXIT automatically. All9 safety flags stayfalse, no production update, no main merge.
'''
 handoff+='\nThe final interface rejects zero remaining regular bars with `NO_REMAINING_REGULAR_BAR`; retain that ENTER as unpriceable/censored rather than opening a fictional position. This handoff guard was added after selection; measured policy/runtime and all replay outputs are unchanged.\n'
 (B/'capital-handoff.md').write_text(handoff)
if __name__=='__main__':main()
