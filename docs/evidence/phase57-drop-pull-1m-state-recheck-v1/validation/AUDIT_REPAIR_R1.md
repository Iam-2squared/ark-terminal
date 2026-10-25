# DROP/PULLBACK 1m State Recheck — audit repair R1

Date: 2026-09-23 JST. Manual continuation; hourly research remains disabled.

## Observed starting state

- PR #587: OPEN / Draft / unmerged.
- Reacquired starting HEAD: `5b47b975b1d833b3992e56ee7dce4010e58e17bb`.
- The one-minute intervention had already been implemented before manual continuation.
- Dedicated run `35815694968`, job `107036623202`, failed at the final causality assertion in `scripts/phase57_drop_pull_1m_state_recheck_v1.py`.
- All 81 focused Python tests passed before that failure. No result summary was published by the failed replay. This is not a performance failure or performance PASS.

## Reproduced audit defect

The scanner searches the complete `inspect.getsource(v3.frozen_intent)` text for forbidden tokens. Its unchanged docstring is `Select first causal intent; never sees quote, fill, Oracle or outcome.` The explanatory word `outcome` therefore makes the static audit FAIL even though it is not an input access. Runtime closed-bar checks must still pass independently.

## Scope of repair

Use Python AST parsing to remove only actual explanatory docstrings (comments are absent from the AST), then scan remaining code with the exact original forbidden-token list. Keep names, attributes, payload keys, other string constants, default expressions and nested executable bodies under audit. Malformed source fails closed. Do not edit the frozen State-v3 classifier or intent engine to hide the word.

Add regression tests for this false positive, every prohibited payload key, executable names/attributes/f-strings, non-docstring literals, default expressions, nested functions, syntax errors, the real frozen function, and current/future suffix invariance. Additionally assert target T0 State parity and exact non-target record parity in full replay. Preserve an audit JSON before failing an assertion so a future failure is diagnosable.

Local isolated tests of the actual new scanner: 7/7 PASS. Full repository tests and the 2,155-opportunity replay are not claimed complete here; they must pass in the subsequent dedicated CI.

## Unchanged research contract

Only initial DROP/PULLBACK receives one-active-minute State rechecks. All six frozen signals remain OR-enabled; T0 BUY states and all non-target policies remain unchanged. No new fallback, threshold change, classifier change, volume layer, provider acquisition, protected evaluation access, EXIT, allocation, promotion, main merge or live/paper execution. Success thresholds remain exactly as precommitted in POLICY_LOCK.json.

Original trial script Git blob: `99094c1b689918390ca205859dd379ed3196c9d4`.
Original trial tests Git blob: `b36f875766a692fa685a83aead2f97b74be2d04a`.
The local copies were verified against those Git blob hashes before editing.

Historical failures and evidence are preserved. This repair authorizes no subsequent hypothesis. Stop after this one-minute measurement and report its result.
