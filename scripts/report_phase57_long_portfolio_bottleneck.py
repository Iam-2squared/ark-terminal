"""Render diagnostic evidence without changing any trading component."""
import json
from pathlib import Path
from scripts.phase57_long_portfolio_bottleneck import OUT, read, digest

def render():
 d=read(OUT/'diagnostic.json'); lines=[]
 def p(s=''):lines.append(s)
 def table(headers,rows):
  p();p('| '+' | '.join(headers)+' |');p('| '+' | '.join(['---']*len(headers))+' |')
  for row in rows:p('| '+' | '.join(str(x) for x in row)+' |')
  p()
 def f(x):return 'UNKNOWN' if x is None else f'{x:,.2f}' if isinstance(x,(int,float)) else str(x)
 p('# Phase57 LONG Portfolio Bottleneck Diagnostic')
 p('Historical / Development / IN-SAMPLE / Outcome-exposed. NOT validated. Source head: '+d['sourceHead'])
 p('No Selector, Entry, EXIT, sizing, threshold or allocation changes. All 277 identities retained. Common173 is a hindsight completeness-selected opportunity subset, of which Equal accepted166. These are observed-price reference replays, not executable-fill or full277 performance claims. Full277 equity remains unresolved. Future labels/extrema/removal sets below are evaluator-only.')
 p('## 1. Coverage')
 c=d['coverage'];table(['Exclusive excluded reason','N'],c['reasons'].items())
 p('65 missing-path cases do not establish missing-data versus no-trade causality. 20 have no remaining regular bar. 19 already resolve the selected LONG exit but fail a different comparison arm: inherited four-arm common coverage is stricter than chosen-exit coverage. Unresolved LONG exits85; missing entry prices0. Overlapping late-session flags37; auction-window flags14, not proven auction-caused gaps.')
 table(['Entry time JST','Included','Excluded'],[(k,v.get('INCLUDED',0),v.get('EXCLUDED',0)) for k,v in c['crossTabs']['entryTime'].items()])
 table(['Coverage','N','Mean E[L]','Mean selector score','Mean rank','30m label N','+1 hits','+2 hits','+3 hits','+5 hits'],[(k,v['n'],f(v['mshScore']['mean']),f(v['selectorScore']['mean']),f(v['selectorRank']['mean']),v['label30Evaluable'],*[v['opportunityHits'][str(t)]['hits'] for t in [1,2,3,5]]) for k,v in c['groups']['coverage'].items()])
 p('Systematic entry-time bias is clear: all28 15:00 entries excluded; 14:30 only3/12 included. Outcome-bias direction is unknown: labels exist for158/173 versus23/104, so observable excluded outcomes cannot represent all104. diagnostic.json includes all277 rows, per-session/symbol/time/cohort cross-tabs and separate included/excluded feature distributions; no imputation.')
 p('## 2. Winner concentration and cash-ledger stress')
 rows=[]
 for k,v in d['concentration']['stress'].items():
  z=v.get('trade'); q=z['closedPnlJpy'] if z else v['performance']['pnlJpy']; perf=z or v['performance']
  rows.append([k,f(v['finalEquityJpy']),f(v['totalReturnPct']),f(v['maxDrawdownPct']),f(perf['profitFactor']),f(q['mean']),f(q['median']),f(100*perf['winRate'])])
 table(['Sensitivity','Final JPY','Return %','DD %','PF','Avg JPY','Median JPY','Win %'],rows)
 p('Top profit symbol89180 contributes334,449.55 JPY over22 accepted trades (145.1% of net profit). Static subtraction leaves−103,918.85 JPY; cash-ledger replay excluding the whole symbol leaves−78,554.375 JPY because later sizing and acceptance change. Top trade is a DIFFERENT symbol90730: Dec30 10:00→11:00,300 shares, entry1101, exit1402, notional330300, PnL90134.85. Removing one trade therefore understates repeated-symbol dependency.')
 p('Removal sets are fixed once from baseline, not repeatedly optimized. They are hindsight stress tests, not tradable exclusion policies. Positive-PnL95% winsorization scales additive contribution curves, leaves losses unchanged, and is NOT a self-financing, lot-compliant replay.')
 table(['89180 entry JST','Exit JST','Entry','Shares','Capital JPY','Exit price','Reason','PnL JPY','MFE %','MAE %','Bars','Rank','Selector score','E[L]','Cohort','Recovered'],[(t['entryTimestamp'],t['exitTimestamp'],t['entryPrice'],t['quantity'],f(t['entryNotionalJpy']),t['exitPrice'],t['exitReason'],f(t['pnlJpy']),f(t['mfe']),f(t['mae']),t['holdingBars'],t['selectorRank'],f(t['selectorScore']),f(t['mshScore']),t['cohort'],t['recovered']) for t in d['concentration']['topSymbolTrades']])
 p('Exact first-bar close, defensive/reclaim transitions and every continuation bar are retained in diagnostic.json. MFE/MAE in the table stop at actual exit; fixed-window extrema are separately retained.')
 p('## 3. Drawdown')
 dd=d['drawdown'];ep=dd['episode']
 p(f"Peak {ep['startTimestamp']} equity {f(ep['peakEquity'])}; trough {ep['troughTimestamp']} equity {f(ep['troughEquity'])}; decline {f(ep['drawdownJpy'])} JPY / {f(ep['drawdownPct'])}%. Recovery: none within observed window.")
 p(f"Realized ledger change {f(dd['realizedChangeJpy'])}; unrealized change {f(dd['unrealizedChangeJpy'])}. The latter is loss of peak unrealized profit, not an assertion of a −51,200 open loss at trough. All equity points reconstruct from individual positions, max error {dd['curveReconciliationMaxErrorJpy']:.3g} JPY.")
 table(['Position','Realized change','Unrealized change','Total DD contribution'],[(r['eventId'],f(r['realizedChangeJpy']),f(r['unrealizedChangeJpy']),f(r['totalEquityChangeJpy'])) for r in dd['positions']])
 p(f"Largest loser57590 Dec25 lost87,385.30 JPY (33.82% of DD):17→13 within3 bars,21,800 shares,370,600 JPY notional. Max concurrent during DD {dd['maxConcurrentDuringDD']}; peak utilization {100*dd['peakUtilizationDuringDD']:.2f}%; sample-mean utilization {100*dd['sampleMeanUtilizationDuringDD']:.2f}% (not time-weighted). Consecutive losing exits {dd['consecutiveLosingExitsDuringDD']}; losing sessions during episode {dd['consecutiveLosingSessionsDuringDD']}; full-window losing-session streak {dd['fullWindowConsecutiveLosingSessions']}. All held IDs retained, including zero contribution.")
 table(['DD hypothesis','Evidence / limitation'],[
 ['A Single catastrophic loser','Material33.82%, insufficient to explain allDD'],['B Multiple correlated losers','Several losses observed, including repeated57590; correlation not established'],['C Excess sizing','Large notional amplifies loss; Rank adds30,464.60 JPY loss to worst trade; optimal size unknown'],['D High concurrency','At most2 in DD; concurrency limit not binding'],['E EXIT latency','Loss occurs within3 bars; no supported counterfactual safer fill/threshold'],['F Entry quality','Large loser E[L]=3.0767; predictive opportunity is not downside protection'],['G Market regime','INCONCLUSIVE: no aligned broad-market evidence'],['H Other','51,200 JPY unrealized-profit reversal plus repeated realized losses']])
 p('## 4. Selector attribution')
 def groups(data):
  return [(k,v['opportunities'],v['accepted'],f(v['pnlJpy']['mean']),f(v['unitNetPct']['mean']),f(v['profitFactor']),f(v['winRate']*100),v['tailMinus10']) for k,v in data.items()]
 headers=['Group','Opportunities','Accepted','Avg JPY','Avg unit %','PF','Win %','<=−10% N']
 table(headers,groups(d['selector']['ranks']));p('Rank4/5:0 observations. Rank1>2>3 average JPY and unit return is descriptively monotonic, but rank3 has only4 observations; conditioned on Entry and included coverage, this cannot establish general ranking calibration.')
 table(headers,groups(d['selector']['scoreQuartiles']));p('Selector-score quartile mean return is nonmonotonic. Quartile boundaries and all opportunity-tier results are in diagnostic.json. Opportunity tier is a future 30m high label, evaluator-only.')
 table(headers,groups(d['selector']['opportunityTier30m']))
 p('## 5. Entry attribution')
 table(headers,groups(d['entry']['quartiles']))
 table(['E[L] quartile','Mean MFE %','Mean MAE %','Mean Equal weight','Mean Rank weight'],[(k,f(v['mfe']['mean']),f(v['mae']['mean']),f(v['equalWeights']['mean']),f(v['rankWeights']['mean'])) for k,v in d['entry']['quartiles'].items()])
 p('MSH E[L] estimates ordinal30m opportunity class, not expected executable net return or risk-adjusted sizing utility. Quartile means are nonmonotonic. Q4 has3/40 accepted losses<=−10%; Q1 has1/40 net winners>=5%. Stronger Q4 aggregate does not prove calibrated sizing. Extrema use complete available Fixed12 reference window, not information used at entry.')
 p('## 6. EXIT attribution')
 table(['Reason','N','PnL JPY','Avg JPY','Median JPY','PF','Median MFE capture','Median giveback pp','Mean pre-exit MAE %','Worst JPY'],[(k,v['pnlJpy']['n'],f(v['pnlJpy']['sum']),f(v['pnlJpy']['mean']),f(v['pnlJpy']['median']),f(v['profitFactor']),f(v['mfeCapture']['median']),f(v['givebackPctPoints']['median']),f(v['preExitMae']['mean']),f(v['pnlJpy']['min'])) for k,v in d['exit']['reasons'].items()])
 p('LONG vs Fixed under Equal: +9,945.10 JPY (+0.99451 initial-capital percentage points); DD20.1692% vs21.3741%, improvement1.205pp. Same166 accepted identities.115 exits earlier,0 later; mean release lead23.55 clock minutes including lunch. Cash releases166 both; same-timestamp recycling5 vs16. MFE-capture denominator is available Fixed12-window high; negative capture permitted.')
 table(['Opportunity MFE','Arm','N','Positive net','Net reaches level'],[(k,a,v['n'],v['positiveNet'],v['realizedAtLeastLevel']) for k,arms in d['exit']['winnerPreservation'].items() for a,v in arms.items()])
 p('BAR5 failure group loss−246,243.75 does not imply dropping those trades would recover this amount: reason is known only after entry. EXIT provides modest portfolio improvement; no evidence here establishes EXIT as the dominant bottleneck.')
 p('## 7. Allocation attribution')
 a=d['allocation'];table(['Rank minus Equal term','JPY'],[(k,f(a[k])) for k in ['commonWinnerEffectJpy','commonLoserEffectJpy','commonQuantityEffectJpy','rankOnlyPnlJpy','equalOnlyPnlJpy','rankMinusEqualJpy']])
 p('Exact identity: +8,619.80 common sizing effect −22,893.60 Rank-only PnL −843.50 Equal-only PnL = −15,117.30. Common resizing is net positive; changed accepted set dominates aggregate underperformance. Rank-only304A0 Dec30 loses23,223 JPY (Equal below-lot), Rank-only50280 Nov27 gains329.40 (Equal cash-blocked); Equal-only36960 Dec30 gains843.50 (Rank below-lot).')
 p('Worst size effect:57590 Dec25 weight0.5→0.6667, shares21800→29400, loss grows30,464.60. Winner89180 Dec9 weight0.5→0.3333 reduces gain15,438. These are material but do not reverse the positive common-set aggregate. Scores, lot rounding, cash and compounding jointly change acceptance. Identical event ordering rules eliminate ordering-policy differences; concurrency-limit rejections0.')
 table(['Capital metric','Equal','Rank'],[(k,f(v),f(a['rankCapital'][k])) for k,v in a['equalCapital'].items()])
 p('Equal accepted166/rejected7 (6 below-lot,1 cash); Rank167/rejected6 (all below-lot). Average utilization8.26% vs8.41%, idle cash91.74% vs91.59%; max concurrency3 vs4. Low utilization is observed, but increasing exposure is not justified by these concentrated, outcome-exposed results.')
 p('## 8. Bottleneck ranking and ONE next action')
 ranking=[
 ['Data Coverage','BOTTLENECK_HIGH','104/277 excluded;85 LONG unresolved; all28 15:00 excluded; full277 equity unknown','Performance direction of missing paths unknown; close marks are not fill proof','A: reconcile existing raw bar provenance/no-trade/session boundary and executable timing; preserve every277 identity'],
 ['Capital Allocation','BOTTLENECK_MEDIUM','Rank−Equal−15,117; worst size shift−30,465; accepted-set delta dominates','Sizing optimum and causal score calibration not established','After coverage repair, frozen paired sizing calibration audit'],
 ['Entry','BOTTLENECK_MEDIUM','Q4 has3/40 deep losers; quartile means nonmonotonic','Opportunity classifier is not sizing utility; no fair alternative tested','After coverage repair, predeclared calibration/tail analysis'],
 ['EXIT','BOTTLENECK_MEDIUM','+9,945 JPY vsFixed; DD improves1.205pp; BAR5 losses−246,244','Reason-conditioned groups not causal intervention; no safe fill counterfactual','After coverage repair, validate frozen exit before considering v2'],
 ['Selector','INCONCLUSIVE','Ranks1>2>3 means monotonic; rank3 N4, rank4/5 N0; score quartiles not monotonic','Entry/coverage conditioning and symbol concentration prevent broad conclusion','After coverage repair, frozen full-event ranking attribution']]
 table(['Component','Judgment','Observed magnitude','Uncertainty','Next test'],ranking)
 p('Choose A ONLY: Coverage / execution semantics. This is the largest evidence bottleneck, not a claim of largest guaranteed PnL uplift. First audit existing caches to distinguish legitimate no-trade, missing data and session-boundary behavior, and remove unnecessary four-arm comparison censoring from descriptive chosen-exit coverage. Do not silently expand performance sample, invent fills, release unresolved cash, or retune a component. Any new execution contract needs separate versioned identity and paired replay. Fresh0; no Validation consumption. Selector/Entry/EXIT/Allocation remain fixed.')
 p('## Verification and safety')
 p('All nine safety flags false; providerRequests0; Fresh0; OOS0; component modifications0; no main merge. Sources and frozen hashes checked before replay; per-position curve and allocation-difference accounting reconcile; deterministic stress replay and evidence hashes tested. Detailed per-entry and position ledgers accompany this report.')
 (OUT/'report.md').write_text('\n'.join(lines)+'\n')
 (OUT/'bottleneck-ranking.json').write_text(json.dumps({'ranking':[dict(zip(['component','judgment','evidence','uncertainty','nextTest'],r)) for r in ranking],'nextAction':'A_COVERAGE_EXECUTION_SEMANTICS_ONLY'},indent=2)+'\n')
if __name__=='__main__':render()
