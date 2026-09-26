# Capital Allocation research handoff

One selected policy: `LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1`. Status `LONG_EXIT_DEVELOPMENT_FINAL_SELECTED_NOT_VALIDATED`.
Manifest: [development-final.json](development-final.json); SHA-256 `e69b4257ec9a9895c939f873740924665fe8b00550bc6ea676054cf23c1f4460`.
Evidence and limits: [report.md](report.md). Historical Development/IN-SAMPLE only; Fresh Validation and OOS remain PENDING.

Use `predict/long-only/phase57_long_exit_development_final.py` as the single research interface. It has no provider, order, broker or v4 dependency. Import by file path, call `new_position(remaining_regular_slots, direction="LONG", cash_equity_only=True)`, then `on_completed_bar(state, bar)` in contiguous expected trading-slot order. `remaining_regular_slots` is calendar-known, not the count of later observed bars. Supply `slot`, `missing`, `c`, `end`, `minutes`; `c=100*(completedClose/unchangedEntryReference-1)`. `end` is the completed bar timestamp and `minutes` is elapsed wall-clock time. Lunch is skipped in trading slots, not wall-clock time.

Return status is `HOLD_RESEARCH_STATE`, `EXIT_REFERENCE`, or `CENSORED`. An emitted EXIT_REFERENCE is final; never append another exit or reuse a closed symbol-session. All same-bar reference fills remain research marks, not broker execution. For truthful executable portfolio simulation, freeze a separate causal fill/latency contract first without silently altering this policy's decisions. Missing bars before exit produce CENSORED; Capital must not discard an unresolved position or assume zero loss, free cash or an invented exit.

Entry stays Threshold2.0, frozen model/scaler/features/ENTER-SKIP; Selector stays Top5 with existing cadence. Entry Historical=BORDERLINE, Fresh Validation=PENDING. Frozen277 identity SHA `72224ac9fd073f7da45c488aaf8ca999752b466e715837c21440e7dd93970236`.

Rules: BAR1 non-adverse including zero -> continuation; adverse -> DEFENSIVE; CLOSE reclaim by BAR5 inclusive -> RECOVERED and reset decline count; no reclaim -> BAR5 close reference exit. Continuation: two consecutive strictly lower completed CLOSEs; equality/rise resets. Maximum12 expected trading bars or shorter calendar cap. Cost0.05pp. Do not substitute session-end, BAR6, analogs or another policy.

Primary evidence173 common pairs from277; standalone selected exit references192. The unpaired104 are not additional evidence of comparative improvement. All76 sessions are exposed; budget195 is untouched. No SHORT/margin/leverage. No allocation optimization or portfolio claims were performed here.

Residual risks: worst reference net -23.5794%; median -0.05%; recovered mean negative; removing best improvement reverses net improvement; same-close fills unproven; post-Nov auction coverage unresolved; closed-trade DD proxies are not portfolio MTM drawdown. Preserve these limits in every downstream report.

Next authorized research topic: integrate the one policy with cash-only capital, overlapping-position/lot/cost accounting and explicit missing/fill handling. Independent Entry/EXIT Validation/OOS remain separate confirmation gates. Do not tune Entry or this EXIT automatically. All9 safety flags stayfalse, no production update, no main merge.

The final interface rejects zero remaining regular bars with `NO_REMAINING_REGULAR_BAR`; retain that ENTER as unpriceable/censored rather than opening a fictional position. This handoff guard was added after selection; measured policy/runtime and all replay outputs are unchanged.
