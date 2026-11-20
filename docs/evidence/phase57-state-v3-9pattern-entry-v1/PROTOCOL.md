# Phase57 State v3 / 9-Pattern Price-Shape Entry v1 — frozen protocol

Status: `POLICY_LOCKED_BEFORE_MEASUREMENT`. Start HEAD is `35e0b5ec20ca05940f34bbe23a5ba29d6d566f72`; population is the unchanged 2,155 Development Opportunities. This protocol implements, but does not alter, `phase57-state-v3-9pattern/CONTRACT.md` and `CONTRACT.json`.

## Causal decision pipeline

For each Opportunity the replay reads the saved full historical path only as a substrate, creates a prefix containing rows whose raw bar start is strictly before NOW, and passes only that prefix plus the actual previous-session path to the State classifier. Raw bar close becomes available at bar-start + one active minute. T0 is the Selector timestamp. State is recomputed at T0 and every five active minutes inside the frozen Entry Timing comparison window. Existing six detector outputs in the saved minute census are checked each active minute. Neither branch receives Oracle, labels, State v2, Entry result or future bars.

At T0, `RISE`, `SHARP_RISE` and `REBOUND` create `INITIAL_STATE_BUY`; the other six states wait. A valid-price `dataQuality=INVALID/state=null` record is impossible by contract; when the input itself is invalid, the retained record waits for a later valid State or existing Signal rather than becoming a tenth State. During WAIT, any one existing Signal creates `SIGNAL_TRIGGER`; a later five-minute transition to any BUY State creates `STATE_TRANSITION_BUY`. There is no fixed-time fallback. Intent persists, and the frozen quote-availability / next-open-plus-5bps fill proxy retries until the existing comparison window ends. An unfilled intent remains `NO_ENTRY` in final throughput while its causal intent reason is retained separately.

## Tie and window semantics

- At T0 a BUY State is primary `INITIAL_STATE_BUY`; all co-firing Signals remain in `triggerSources`.
- After T0, if Signal and State transition first occur at the same timestamp, `triggerSources` contains both and primary intent reason is deterministically `SIGNAL_TRIGGER`.
- Tie priority cannot alter trigger timestamp, attempted price or fill.
- Decision observation runs from T0 through T+30 active minutes and includes a closed checkpoint that coincides with the 11:30 or 15:25 boundary. Fill attempts retain the existing `comparisonEligible` grid, which excludes non-executable lunch/session boundary instants. Thus a T0=11:30 intent persists to the first afternoon fill attempt without counting lunch as elapsed time. The window never extends beyond 15:25 JST.
- Missing observation is retained as missing. It is not inferred as no-trade or halt.

## Contract operationalization fixed before measurement

Recent coverage uses expected regular bar starts in the up-to-ten-active-minute interval ending at NOW; latest expected closed bar absent means stale. Stop classification requires 100% such coverage. When a flat recent segment is near the prefix extreme but coverage is missing/stale, it cannot prove a Stop and carries the prior `RISE`/`DROP` direction with LOW confidence. A 09:00 raw bar supplies the official open; otherwise the earliest observed close anchors the episode and quality is DEGRADED. Previous scale uses only same-auction, consecutive observed one-minute previous-session closes. All equality boundaries follow the STEP 1 Contract.

## Evaluator separation and comparisons

Every causal State checkpoint, first Signal, first BUY-State transition and intent is fixed for all 2,155 records before quote/fill rows, Oracle Opportunity records or future labels are opened. Evaluator output compares frozen Immediate, frozen Signal-only, frozen State-Conditioned Signal Entry v1, and this State v3 Entry. Oracle Low/High, Capture, MFE/MAE and wait missed-upside are evaluator-only.

No State v2 agreement target, labels, training, threshold search, Volume, Dictionary, new Signal, EXIT, Capital, Portfolio, Common Holdout, Fresh, OOS, Prospective, provider request, main merge or trading is authorized. Safety9 remain false. Results cannot change this policy in the current run.
