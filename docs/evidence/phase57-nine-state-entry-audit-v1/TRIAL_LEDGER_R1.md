# Phase57 9-State Entry Audit — Trial Ledger R1

2026-09-24 JST. Append-only bounded-pass ledger under `PROTOCOL_R0.md`.

All 2,155 Opportunities are already outcome-exposed Development. This ledger is an engineering trial-exposure record, not a claim of independent validation. A performance hypothesis is counted only when a decision rule was precommitted and then replayed against evaluator outcomes. Diagnostic-only attribution and software-plumbing repairs do not consume a State performance slot.

| State | T0 N | trial | precommit / run | result | slot |
|---|---:|---|---|---|---:|
| REBOUND | 192 | confirmation candidate | precommitted before replay; run `35865392687` | REJECT — EntryPosition improved but Fill collapsed to about 38% | 1/1 consumed |
| RISE | 111 | `CONFIRMED_BUY_PERSISTENCE_V1` | `CONFIRMED_BUY_PERSISTENCE_HYPOTHESES_R1.md`; run `35897369272` | REJECT — preservation and threshold-rate Gates failed | 1/1 consumed |
| SHARP_RISE | 7 | none | diagnostic only | INSUFFICIENT_FOR_PERFORMANCE_RULE | 0/1 unused |
| DROP | 1403 | `CONFIRMED_BUY_PERSISTENCE_V1` | `CONFIRMED_BUY_PERSISTENCE_HYPOTHESES_R1.md`; run `35897369272` | REJECT — paired EntryPosition/Low distance worsened; Fill/Capture Gates failed | 1/1 consumed |
| PULLBACK | 354 | `CONFIRMED_BUY_PERSISTENCE_V1` | `CONFIRMED_BUY_PERSISTENCE_HYPOTHESES_R1.md`; run `35897369272` | REJECT — aggregate appearance did not survive common-case paired comparison; Fill/Capture Gates failed | 1/1 consumed |
| RANGE | 57 | none | remaining-State diagnostic run `35909289314` | HOLD — no justified single causal hypothesis without outcome-derived delay | 0/1 unused |
| SHARP_DROP | 26 | none | remaining-State diagnostic run `35909289314` | HOLD — limited support and no justified single causal hypothesis | 0/1 unused |
| DROP_STOP | 5 | none | diagnostic only | INSUFFICIENT_FOR_PERFORMANCE_RULE | 0/1 unused |
| RISE_STOP | 0 | none | T0 + transition/code audit | NO_OBSERVATIONS / INSUFFICIENT_FOR_PERFORMANCE | 0/1 unused |

## Rejected-trial preservation

No rejected candidate is silently replaced by a second unattended hypothesis. In particular:

- REBOUND is not retuned after the Fill-collapse rejection.
- RISE, DROP and PULLBACK do not receive a persistence-length sweep, alternate confirmation threshold, alternate frozen Signal combination or other result-following retry.
- RANGE and SHARP_DROP slots remain unused because an unused slot is not permission to invent a trial from evaluator-Low timing. Their accepted policy already waits for the first existing frozen Signal or transition to an existing BUY State; further delay requires a new persistence criterion, and no such criterion was causally justified before performance replay.
- SHARP_RISE and DROP_STOP are not promoted from tiny samples by weakening support standards.
- RISE_STOP is not populated by changing State thresholds.

## Infrastructure / diagnostic events not counted as performance trials

- REBOUND blind-review packet cardinality/assertion repairs: software/workflow plumbing only.
- Blind chart/witness transport and sealed-scoring workflows: semantic audit infrastructure only.
- Common Nine-State anatomy v1/v2: evaluator reporting only.
- Remaining-State Low-Centered Attribution v2: diagnostic-only by precommit.
- run `35902412560` failure `ModuleNotFoundError: No module named 'scripts'` and repair commit `f05fb2c3db13101f6efaf59d56d91cc581055b6f`: workflow Python-path repair only; corrected run `35909289314` preserved the same diagnostic protocol.

## Bounded-pass total

- maximum authorized new performance hypotheses: 9
- actually evaluated new State-level performance hypotheses: 4
- accepted: 0
- rejected: 4
- unused because insufficient/no justified hypothesis/no observations: 5
- threshold sweeps / win-until-PASS loops: 0
- new Signal / Volume / Dictionary / learned model / State semantic change: 0
- protected Fresh/OOS/Validation opens: 0

The bounded pass is therefore closed without an adopted Entry modification. Further performance experimentation requires a new research authorization or a new causally justified information source/architecture rather than reusing this exposed Development set to keep trying variants.
