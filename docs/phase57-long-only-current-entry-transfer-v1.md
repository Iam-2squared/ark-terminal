# Phase57 LONG-only Frozen Selector v1 × CURRENT Entry transfer diagnostic

**Final verdict: `CURRENT_ENTRY_FILTER_PROBLEM`**

## Scope and integrity

- JPX cash equity, LONG-only. SHORT scores, margin and leverage were not used.
- Frozen Selector and CURRENT Entry weights/threshold/features were read only; fit calls: 0.
- Development only: 76 sessions, 760 timestamps, 3800 Top5 events.
- Validation/OOS remained sealed. EXIT and Capital Allocation were not used.

## Funnel

| Status | Events | Rate |
|---|---:|---:|
| PASS | 162 | 4.26% |
| REJECT | 753 | 19.82% |
| WAIT | 956 | 25.16% |
| BLOCKED | 1929 | 50.76% |
| UNAVAILABLE | 0 | 0.00% |

CURRENT Entry has no immediate REJECT label; REJECT appears only after terminal EXPIRED state and later reselection.

## Primary diagnostics

| Metric | Value |
|---|---:|
| First-entry symbol-session coverage | 3.50% |
| +3 opportunity preservation | 6.64% |
| +5 opportunity preservation | 9.50% |
| Median first-pass latency | 0.0 min |
| Median consumed return | 0.0 bps |
| Entry-time +3 remaining retention | 92.00% |
| Entry-time +5 remaining retention | 100.00% |

## Verdict basis

- Filter problem: `True` — opportunityPreservation3Below60Pct, opportunityPreservation5Below60Pct, symbolSessionFirstEntryCoverageBelow20Pct
- Latency problem: `False` — 

This is a cross-era Development transfer diagnostic, not a Validation/OOS or causal historical performance claim. MSH_ENTRY_V1 was trained after the Selector Development dates, but its saved weights are applied without fitting and without using these Selector outcomes.

STOP: no new LONG Entry, threshold, feature, model or WAIT redesign is created by this result.
