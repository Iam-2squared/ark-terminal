# Phase57 fresh R3 local verification — IN PROGRESS, not A12

Recorded: 2026-09-22 20:50 JST
Repo: Iam-2squared/ark-terminal
Branch: research/phase57-long-only-cash-equity
PR: #587 — Open / Draft / not merged
Turn start HEAD: f16f977723f12667c8f5bac6c2248ddca127ecf9
Latest observed HEAD before this checkpoint: 3ec201c66ca53f566c8e232481a8eb96d0d53283
Local R3 source snapshot HEAD: 420efbced9d546c826d9a08c3a35969ddbaf8c78
Existing full-completion CI execution HEAD: b784e97ac6a5bd1b97a62af4923423596a1258c6

## Actually executed in this runtime
- Recovered and byte-verified original primary source artifact10683107105, all four pinned Development artifacts10605887642/10619378314/10621869067/10630618102, original baseline10682598898 and A8 recovered raw-fact artifact10688737280.
- Recovered exact R3 28-file source bundle: XZ SHA256 b66b369c3c767f9e69dd2a78569b598912205bccdfeb030b95b37826147f9c7b; decoded SHA2566ed039a0b5e9fa96201e341291b31b9e2f57ab3cfc22ca25d949d3e3c55913e5. Every member hash verified. No R3 numerical source was edited.
- Executed original frozen G admission locally, retained2,155 tasks, verified exact original input projection and generated58 bounded-memory session partitions.
- Executed all322 assertion executions PASS: primary158, new A8 parser/admission45, independent reused numerical/Golden119. The119 reused assertions are not119 new test designs or an external human review.
- Regenerated A8 decisions exactly: canonical2e29f37afee6ca9a673006b045dd98b5da6e3b0aa0eadd7edc197f4e42e8e900; original admission receipt8292eb6cb35be88a84e7efc5f4814853b1d5febb6d76596a76d2a72c048f666e retained.10,547 raw Daily projection matches;10,307 admissible lag primitives /240 new masks /228 inherited unavailable. No prior rejection was promoted.
- Executed historical timestamp/context audit PASS:704,991 normalized regular-row comparisons,6,701 auction-sidecar rows,2,155 exact lag sets,2,112 full previous-context matches,2,111 Scale block-witness matches and6 predeclared raw minute witnesses. No fabricated receivedAt or missing-witness replacement.

## Full-population work still executing
Two separate fresh R3 runs are executing in this runtime, not merely copied from a delivered R2 report:
1. Normal order /2 workers /PYTHONHASHSEED23.
2. Reverse order /3 workers /PYTHONHASHSEED47, full future-suffix routing mutation plus fresh suffix-removal checks.
Both rebuild all77,214 NOW and Future references and compare every field and numerical snapshot to the separate R3 implementation. Final manifests and all-row totals are NOT yet asserted here. Their completed canonical output hashes are intended for exact comparison to each other and CI35721458178; unlike the older delivered R2 implementation, these runs use the identical R3 numerical bundle.

Additional strict baseline-v2-to-A8-v2 full-row transition, schema, event and replay/coverage auditors are staged. They cannot pass on partial outputs. No competing CI publication workflow was launched; the existing full-completion run35721458178 is being reused. Its322 tests, A8 regeneration and timestamp/context steps passed; the full reverse independent step remained IN_PROGRESS at last inspection.

## Failure preservation and scope
The first local staging interpreter cached a then-nonexistent PYTHONPATH directory and failed an import. The failed log is retained. A fresh interpreter reran the same source successfully; no numerical code or pin was modified. CI's separately pinned importlib cache-invalidation repair is a documented bootstrap-only difference, not a numerical change. Original R2 mismatches, earlier recovery failures and the prior whole-cache R3 memory failure remain preserved.

A8 is HISTORICAL_CLOSED_RECONSTRUCTION only, not receipt/announcement latency or prospective parity. Minute-start semantics are a documented raw-witness/official-session inference, not a verbatim claim in the provider Time field description. A9 is same-assistant second-implementation verification with post-comparison R3 corrections, not external human/Claude approval.

## Runtime continuity
Work root: /mnt/data/state-v2-finish.
Logs: execution-logs/r3-local-attempt2.log and r3-local-reverse.log; corresponding .exit files appear on termination.
Outputs: round3/generation-local-normal and round3/generation-local-reverse.
Dependency audits and failures have distinct logs; never replace an earlier output directory. These are runtime paths, not repository raw-file locations.

Frozen State design/engine/Scale/H10/Selector/cohort unchanged. Safety9 all false; providerRequests=0; protectedDataOpened=0. No Recognition, model fitting, Signal, Entry/EXIT/Capital, main merge or trading. A12 remains unissued by this runtime until every required result is actually verified.
