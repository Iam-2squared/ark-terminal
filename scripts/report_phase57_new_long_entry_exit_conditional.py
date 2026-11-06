"""Render the saved conditional EXIT measurements; no replay or tuning."""
from scripts import phase57_new_long_entry_exit_conditional as d

def fmt(x):return 'N/A' if x is None else f'{x:.4f}'
def fraction(r):return f"{r['n']}/{r['denominator']} ({fmt(100*r['rate']) if r['rate'] is not None else 'N/A'}%)"
def render():
    s=d.read(d.BASE/'summary.json');lines=[]
    def add(x=''):lines.append(x)
    add('# Phase57 Frozen NEW LONG Entry v1 × Existing LONG EXIT')
    add('\nDate: 2026-09-18 JST. **Decision: BUILD_NEW_LONG_EXIT** (Development research disposition only).')
    add('\nMechanical transfer **PASS for both INITIAL and DIP_REPRICE**. Unchanged policy replay is possible; '
        'mechanical compatibility does not establish suitability. Existing EXIT improves some tails, but DIP average/PF/winner capture '
        'deteriorate and the exact additional-downside106/21 cohorts have worse mean outcomes. Retain the existing policy as a frozen control/foundation; '
        'do not adopt it as the completed new two-opportunity EXIT. This is a design judgment on exposed Development, not proof '
        'that another policy will outperform, a numerical acceptance-gate pass, or an OOS/Portfolio claim.')
    add('\n## Audit / exact lineage')
    add('\nStarting remote HEAD `efa7efb5235dcb1b711599d5c0ba0a196ec5fab9` exactly matched the handoff; PR #587 open/Draft/unmerged. '
        'PR body was stale and was not used as Entry authority. Freeze / Contract / Parity were read at the pinned snapshot. '
        'Frozen implementation/evidence `6fabde7dfe208e19d5611e0a290b4df6724e562e` remains unchanged.')
    add('\nSaved parity run35250519787/job105301441720 SUCCESS; artifact10508583428 ZIP and all3 files independently hash-verified. '
        'No Entry study/kernel replay was run for this diagnostic. Initial HEAD CI API returned6 successful checks and4 skipped '
        'research workflows (skipped is not a pass); existing parity CI at that HEAD was already successful.')
    add('\n| Lineage | Exact evidence / applicability |\n|---|---|')
    add('| Existing selected LONG EXIT | `LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1`, freeze `ba0ccdb2aea7e5fc9fee817c0bd95f09427108f8`; `LONG_EXIT_DEVELOPMENT_FINAL_SELECTED_NOT_VALIDATED` |')
    add('| Runtime/interface | `predict/long-only/phase57_long_exit_continuation_v1.py` / `phase57_long_exit_development_final.py`; exact hashes in contract and manifest, unchanged |')
    add('| Prior selected-population evidence | 277 old MSH ENTER identities, common173; mean+0.370759%, PF1.254518, worst−23.579412%; these are not current cohort results |')
    add('| v3/v4 | Frozen analog dependency uses56-day window ending2026-08-12; all dates after this target2024-09-17–2025-01-09 period. PIT requires analog.sessionDate < entry.sessionDate and fullyRealizedAt < decision. Eligible frozen analog rows0. No new pool built |')
    add('| v5 BAR5 | `EXIT_V5_DYNAMIC_RECLAIM_BAR_5`, candidate417ad9d6dc92c3110e680cdc4a6c8dcf94b4ee5e, simulatoraaa99030295ffb447de273881b16aad1eab1a7e9; mechanical parity but blocked on original causal v4 result/trace. Not silently replaced by BAR6 or Fixed12 |')
    add('| Newer LONG policy dependency | No model/analog/train period. Designed/selected on exposed old277 Development; transfer is a different population and reference location |')
    add('\nThe old EXIT freeze commit has4 successful PR-triggered CI workflows in the queried API page, including Predict Tests, '
        'Historical Re-Measurement Integrity and LONG-only Research Foundation. The API only returns PR-triggered runs; '
        'absence of a dedicated EXIT workflow in that page is not a claim it never ran. Current focused local tests:17/17 PASS '
        'under kernel Internet-socket denial, including frozen runtime/state tests, evidence pins and new transfer tests.')
    add('\n## Research interface and execution limits')
    add('\nSee contract.md, committed locally before measurement as9d87997 (direct git push lacked credentials; connector publication follows measurement, '
        'so this is **not remote preregistration**). INITIAL and DIP are independent hypothetical funded unit positions at the exact saved OPEN reference. '
        'No automatic funding, combined return, notional, cash allocation or Entry mutation. DIP starts at its saved opportunity timestamp, with a new state '
        'and price-rebased CLOSE; no pre-DIP OHLC or state. EXIT uses only completed CLOSE, inherited BAR5 reclaim, two lower CLOSEs, '
        '12-trading-bar/calendar cap and0.05pp round-trip cost. Missing before exit censors; missing after exit cannot alter the exit.')
    add('\nReference OPEN and contemporaneous decision-CLOSE exit are optimistic marks, not executable fills. Zero latency/queue/slippage is an explicit '
        'research assumption; actual execution remains unresolved. Bar count skips lunch; clock time includes it. Strict wall-clock diagnostic horizons '
        'never cross lunch. SAFE_REGULAR_END is15:00 before2024-11-05 and15:25 thereafter, excluding the unresolved auction gap; '
        'this separate diagnostic does not modify the inherited EXIT calendar cap. No overnight, interpolation, missing-flat fill, or provider substitution.')
    add('\n## Population / same-identity comparison')
    add('\n| Cohort | Opportunities | Priced reference | Existing standalone | Fixed12 standalone / paired | Original primary subset paired |\n|---|---:|---:|---:|---:|---:|')
    for name,v in s['cohorts'].items():add(f"| {name} | {v['opportunities']} | {v['referenceEligible']} | {v['existingStandaloneN']} | {v['fixedStandaloneN']} / {v['paired']['pairedN']} | {v['primary60Subset']['pairedN']} |")
    add('\nINITIAL retains all2743 anchors:483 missing references and353 expired;675 more censor before existing EXIT. '
        'DIP retains exactly541 emitted opportunities;92 censor before existing EXIT. Standalone existing results are never compared against a smaller '
        'Fixed12 population. The original dip328 primary panel becomes324 paired for an own-start12-bar EXIT comparison: '
        '4 lack the extra required post-DIP coverage; the original328 are not dropped from the ledger. Trading-bar EXIT eligibility can exceed '
        'strict wall-clock+60 eligibility because EXIT may skip lunch or use a shorter known session cap.')
    add('\nAll return sums and DD below are unweighted percentage-point sums/proxies, **not Portfolio return or portfolio MaxDD**. '
        'N differs between INITIAL and DIP; do not add them or infer a fund-all policy.')
    add('\n| Cohort / arm | N | Net sum pp | Mean % | Median % | Win rate | PF | Worst % | p05 % | Worst5% mean % | Entry-order DD pp | Exit-order DD pp |\n|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|')
    for name,v in s['cohorts'].items():
        for arm in ('fixed','existing'):
            r=v['paired'][arm];p=r['netPct']
            add(f"| {name.split('_')[0]} / {arm} | {r['n']} | {fmt(r['netSumPP'])} | {fmt(p['mean'])} | {fmt(p['median'])} | {fraction(r['winRate'])} | {fmt(r['pf'])} | {fmt(p['min'])} | {fmt(p['p05'])} | {fmt(p['worst5Mean'])} | {fmt(r['entryOrderDDProxyPP'])} | {fmt(r['exitOrderDDProxyPP'])} |")
    add('\n| Cohort / arm | Mean holding bars | Mean clock min | Mean pre-exit MAE % | Median MFE capture | Capture N | Mean giveback pp | Median giveback pp |\n|---|---:|---:|---:|---:|---:|---:|---:|')
    for name,v in s['cohorts'].items():
        for arm in ('fixed','existing'):
            r=v['paired'][arm]
            add(f"| {name.split('_')[0]} / {arm} | {fmt(r['holdingBars']['mean'])} | {fmt(r['holdingClockMinutes']['mean'])} | {fmt(r['preExitMaePct']['mean'])} | {fmt(r['mfeCapture']['median'])} | {r['mfeCapture']['n']} | {fmt(r['givebackPP']['mean'])} | {fmt(r['givebackPP']['median'])} |")
    add('\nMFE capture=gross reference exit/common Fixed12-window MFE, undefined if MFE<=0. This is a ratio, not realized HIGH execution. '
        'A negative value means closing below the entry reference despite a positive observable high.')
    add('\n| Cohort | Existing exit reason on paired population |\n|---|---|')
    for name,v in s['cohorts'].items():add(f"| {name} | {v['paired']['existing']['reasons']} |")
    add('\n## Conditional path diagnostics')
    add('\nOwn position-start horizons; each row has its own complete-case N. Time-to-MFE/MAE is recorded as the containing bar interval, '
        'not an invented exact intrabar time. First-positive/recovery uses completed CLOSE; recovery after an adverse LOW requires a later bar. '
        'summary.json contains distributions, times, +1/+2/+3/+5 hits, adverse/recovery rates and deep-downside outcomes; ledger.json.gz retains every event.')
    add('\n| Cohort | Horizon | N | Median CLOSE % | Median MFE % | Median MAE % | Median giveback pp | +3 reach | +5 reach |\n|---|---|---:|---:|---:|---:|---:|---|---|')
    for name,v in s['cohorts'].items():
        for h in (*map(str,d.HORIZONS),'SAFE_REGULAR_END'):
            r=v['path'][h]
            add(f"| {name.split('_')[0]} | {h} | {r['n']} | {fmt(r['closePct']['median'])} | {fmt(r['mfePct']['median'])} | {fmt(r['maePct']['median'])} | {fmt(r['givebackPP']['median'])} | {fraction(r['reach']['3'])} | {fraction(r['reach']['5'])} |")
    add('\n## +3/+5 winner preservation')
    add('\n| Cohort / arm | Level | Available winners | Final net positive | Final net >= level | Exit before first HIGH touch |\n|---|---:|---:|---|---|---|')
    for name,v in s['cohorts'].items():
        for arm in ('fixed','existing'):
            for k in ('3','5'):
                r=v['paired'][arm]['winners'][k]
                add(f"| {name.split('_')[0]} / {arm} | {k} | {r['n']} | {fraction(r['finalNetPositive'])} | {fraction(r['finalNetAtLeastLevel'])} | {fraction(r['exitBeforeFirstHighTouch'])} |")
    add('\nSame-bar touch and exit are not classified as premature; HIGH/LOW order is unknown. Positive final net and reaching the full level are different measures.')
    add('\n## Exact cheaper-DIP106 /21 risk cases')
    add('\nAll original primary328 → cheaper299 → additionalD30>=2%106 / >=5%21 identities were matched to the saved parity ledger. '
        'Both risk subsets have complete paired EXIT results for every requested identity. Thresholds select evaluator-only retrospective diagnostics, never Entry/EXIT inputs.')
    add('\n| Subset | Paired N | Fixed mean % | Existing mean % | Fixed worst % | Existing worst % | Fixed p05 % | Existing p05 % | Existing exit before / same / after adverse bar |\n|---|---:|---:|---:|---:|---:|---:|---:|---|')
    for k in (2,5):
        r=s['riskSubsets'][f'CHEAPER_PRIMARY_D30_{k}'];a=r['fixed']['netPct'];b=r['existing']['netPct']
        add(f"| D30 >= {k}% | {r['pairedN']} | {fmt(a['mean'])} | {fmt(b['mean'])} | {fmt(a['min'])} | {fmt(b['min'])} | {fmt(a['p05'])} | {fmt(b['p05'])} | {r['exitTiming'][str(k)]} |")
    add('\nIn the106 group,31/106 recover at a later completed CLOSE within ownD30, but88/106 finishD30 below reference. '
        'In the21 group,1/21 later-close recovery and20/21 negativeD30 close. These definitions can overlap (recover then fall again). '
        'Later bar +3/+5 after >=2% downside:10/106 and5/106; after >=5%:0/21 and0/21 inD30. Same-bar recoveries/winners are not assumed.')
    add('\nExisting EXIT strictly precedes the threshold bar for only14/106 and3/21; same-bar15/106 and5/21 remain conservatively uncredited, '
        'after-bar77/106 and13/21. It reduces average pre-exit MAE but does not improve average final reference PnL in either subset. '
        'The21-case p05 actually worsens even as its single worst loss improves. Consequently “Dip is safe” or “risk solved” is not supported.')
    add('\n## Coverage / sensitivity / interpretation')
    add('\n| Cohort / panel | N | Fixed mean % | Existing mean % | Fixed PF | Existing PF |\n|---|---:|---:|---:|---:|---:|')
    for name,v in s['cohorts'].items():
        for panel in ('primary60Subset','fullUnderlyingMinutesPaired'):
            r=v[panel];add(f"| {name.split('_')[0]} / {panel} | {r['pairedN']} | {fmt(r['fixed']['netPct']['mean'])} | {fmt(r['existing']['netPct']['mean'])} | {fmt(r['fixed']['pf'])} | {fmt(r['existing']['pf'])} |")
    add('\nFull-underlying-minute sensitivity uses only saved observedMinutes metadata, not new1m data. Sparse coverage, informative missingness, '
        'same-data architecture exposure, overlapping unit positions, and execution assumptions prevent generalization/portfolio claims. '
        'The retained median-PnL and winner losses are not evidence to retune Entry; old277-selected EXIT success cannot be transferred to these populations.')
    add('\n## Disposition and minimal next architecture (proposal only)')
    add('\n**BUILD_NEW_LONG_EXIT** is the research recommendation because mechanical adaptation alone leaves the measured DIP risk/upside problem. '
        'It is not a declaration that every existing mechanic failed: first-bar routing, reference-relative reclaim, causal completed-bar state, '
        'missing handling and session cap are reusable. INITIAL has modest average/tail improvement but negative mean and lower winner preservation; '
        'there is no basis to call the whole pipeline improved.')
    add('\nA minimal first challenger can reuse the same state machine and the already-existing **two consecutive lower completed CLOSEs** condition '
        'as an early breakdown exit while DEFENSIVE, before the inherited BAR5 no-reclaim deadline. Keep reclaim priority at CLOSE>=0, reset state at '
        'each actually funded position, and keep continuation/cap/cost unchanged for that single comparison. This isolates the current policy’s '
        'DEFENSIVE wait risk without a stop/TP/trailing/VWAP grid, new feature, symbol rule, or Entry change. It is only a concrete unmeasured proposal; '
        'it may cut eventual recoveries and cannot be assumed to repair continuation’s premature winner exits. Do not add another continuation variant automatically.')
    add('\nBefore any challenger result, pin its exact decision ordering and compare that one modification on identical identities, with tail AND winner metrics. '
        'No new policy code or challenger replay was created in this task. The requested audit/conditional replay/architecture decision is complete. '
        'Fresh/OOS remains sealed until separately predefined integrated validation after Selector→Entry→EXIT→Allocation→Portfolio is fixed.')
    add('\n## Reproducibility and artifacts')
    add('\n- `contract.md`: interface, lineage, assumptions and measurement plan.\n- `entry-parity/`: exact original saved opportunity inputs.\n- `summary.json`: all requested aggregate metrics and explicit denominators.\n- `ledger.json.gz`:3284 separate cohort records, path timing/risk/exit details.\n- `manifest.json`: immutable input/output hashes and zero counters.\n- `audit.json`: remote/CI receipts, publication boundary and scope.\n- `scripts/phase57_new_long_entry_exit_conditional.py`: deterministic offline evaluator.\n- `scripts/test_phase57_new_long_entry_exit_conditional.py`: integrity tests.')
    add('\n```bash\nARK_TEST_OFFLINE=1 python3 scripts/offline/kernel_exec.py python3 -m scripts.phase57_new_long_entry_exit_conditional --out /tmp/phase57-exit-repro\nARK_TEST_OFFLINE=1 python3 scripts/offline/kernel_exec.py python3 -m unittest scripts.test_phase57_new_long_entry_exit_conditional\n```')
    add('\nAll9 safety flags remain false. Selector/Entry/Allocation/legacy EXIT unchanged; no market provider acquisition, '
        'model fit, analog pool, Fresh/OOS opening, live/paper order, production promotion or main merge. '
        'The research branch remains Draft/unmerged. CI success verifies integrity only.')
    (d.BASE/'REPORT.md').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':render()
