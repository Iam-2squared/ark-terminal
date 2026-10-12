# Phase57 State v3 — STEP 1 definition freeze receipt

Status: `STEP1_COMPLETE_STOP`; no STEP 2 authorization.

| Item | Frozen receipt |
|---|---|
| PR / branch | #587 / `research/phase57-long-only-cash-equity` |
| Start HEAD | `ca3e0fe6982d5e8e5b54de551bac5ca4f3e3f009` |
| Contract + manifest CI HEAD | `985414aa2ec8ec516c4c9781384736b7168fb0da` |
| Nine IDs | RISE_STOP, RISE, SHARP_RISE, PULLBACK, RANGE, REBOUND, SHARP_DROP, DROP, DROP_STOP |
| Dedicated static tests | 7/7 PASS locally and in GitHub Actions |
| Dedicated CI | Run `35803937783`, job `107000364358`, PASS |
| Existing Predict Tests | Run `35803938704`, job `107000366652`, PASS |
| Contract/CI content hashes | `MANIFEST.json` (SHA-256 of four source files; verified by test) |
| Prior frozen artifacts | Not modified; commits add only this namespace, one test, one workflow |
| Provider requests / protected partitions | 0 / unopened |

The nine names draw on Rakuten's daily-chart vocabulary; this is Ark's independent intraday price-shape contract. The total-classification claim is **normative for valid charts**, not an empirical 2,155-case coverage result. Null state with `dataQuality=INVALID` is explicitly retained and must not be represented as a tenth state or dropped from future accounting. Prior-day plus current completed-bar causality, publisher availability, active-session boundaries, normalization, exact thresholds, nine-cell tie-break, short history, invalid reasons and separate confidence are fixed in `CONTRACT.md`/`CONTRACT.json`. Volume is reserved for a distinct later layer.

The broad PR CI includes five failing legacy workflows at this snapshot: `Phase57 EXIT CC Freeze Audit`, `Phase57 Causal Entry State Path Anatomy v1`, `Phase57 State v2 Bootstrap Audit`, `Phase57 G Five Minute Reference v1`, `Phase57 Causal Entry Daily Ablation Completion Audit`. These are **not** reported as green. For example, the causal Entry failure is a pre-existing immutable pin mismatch on `.github/workflows/phase57-causal-entry-state-v1.yml`; that file was not changed in either STEP 1 commit. Neither old evidence nor its pin is amended here. Targeted Contract CI and existing Predict Tests passed.

Open items for human review: whether the independent 10-active-minute segment, floor `log(1.001)`, prior-session scale, stop-eligibility density, and reversal-magnitude boundary faithfully express the intended nine visual patterns. These are fixed STEP 1 choices, not validated predictive findings. Changes require a new contract version and explicit authorization. STEP 2 must implement synthetic-path partition/causality tests and report actual invalid-data coverage before replaying 2,155 records.

Safety9: `executionAllowed=false`, `brokerWriteAllowed=false`, `excelOrderWriteAllowed=false`, `rssOrderFunctionAllowed=false`, `liveTradingAllowed=false`, `paperTradingAllowed=false`, `automaticPromotionAllowed=false`, `productionUpdateAllowed=false`, `transmitted=false`.

STOP: no classifier, volume layer, Entry/EXIT/Capital/Portfolio modification, Dictionary ingestion, Holdout/Fresh/OOS/Prospective opening, main merge, paper or live trading.
