# Capital V5.1 RESET20 / R5-R10 cycle

Policy ID: V5.1, precommit `ec555d31354fe05b6046a1c272d2db2724708cac`.
Result: rejected; median endpoint cash falls on the 9/21 measurable Development
windows. 12 coverage-blocked windows remain in the planned manifest.

The immutable V5 engine is loaded from
`research/capital-v5-max3-slot-intelligence-20261004-v1/`, authority commit
`710656491be06235901b45c50a8b5cbd714ba4eb`. No model fitting is performed.
The new allocator is a separate function injected into a separate day-engine
function object; the original module's globals/code are unchanged.

The original instruction, hashes, source-member bindings, window manifest,
precommit and all aggregate evidence are in the matching docs/evidence directory.
Private price/identity ledgers and evaluation labels are retained in the private
delivery ZIP, whose exact SHA256 and authenticated reference are recorded there.

For source recovery in another environment, use `resolve_inputs.py` with the
actual paths of the supplied MAIN_CAPITAL_2X, V9 and V11R1 ZIPs. It traverses nested
archives once per archive SHA, resolves members from the original INPUT_BINDING
and exact byte hashes, and records the current local paths. Preserve each frozen
input's hash; never use old scratch paths or regenerate upstream candidates.
V4 dataset/acquisition metadata checked for the 2 missing dates is documented
separately in COVERAGE_AND_WINDOWS.json. Its zero-entry completeness was not
established. Do not rerun `prepare_scope.py` to invent a different calendar set.

The completed cycle's order was: prepare_scope -> test_reset20 + test_labels ->
r_labels (one materialization) -> V5 batch -> independent accounting -> diagnostic
and local cash/lot constraints -> candidate draft -> test_v51 -> precommit/readback ->
candidate batch -> independent accounting -> final comparison/plots.
Candidate synthetic tests were completed before the precommit was saved; neither
formal candidate outcomes nor any alternate-policy replay was used to tune it.

`run_policy.py` resets cash only at each window start and calls the original V5
day engine with each explicit session. It stops a window at its first execution
failure; successful saved window checkpoints are reused on technical resume.
The account is already flat at the end of each complete native day, as required
by the inherited EOD contract. Market history, score/model schedule and arrival
tables are never reset. Labels are not imported by either allocator.

`accounting_audit.py` separately uses raw source O/C, original cost factors and
saved quantities to reconstruct BUY/SELL, every cash/MTM frame, positions,
daily carry and window endpoints. It does not import execution/allocation/replay
functions. Window overlap is not treated as independent statistical sampling.

Dedicated checks: evaluator 12 tests, R-boundary 3 tests, candidate 11 canaries,
one saved-market-day exact comparison, raw-source accounting 18 windows, all pass.
The normal formal budget is exhausted: one V5 batch and one V5.1 batch. This
README describes reproducibility; it does not authorize new fits, another policy
or another formal batch in this cycle. Selector/Entry/EXIT remain frozen.
