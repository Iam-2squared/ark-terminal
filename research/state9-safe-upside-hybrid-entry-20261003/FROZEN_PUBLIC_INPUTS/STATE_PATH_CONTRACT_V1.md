# State Path / Transition Contract V1

Document: STATE_PATH_CONTRACT_V1_20261002
Authority: WORK_STATE_PATH_TRANSITION_MAX_THROUGHPUT_20261002_V1.
Parent cycle: STATE9_RC2_MARKET_SEMANTIC_AUDIT_20261001_V1.
Stage: STATE_PATH_TRANSITION_20261002_V1.
Status at fixation: DEFINITION_FIXED_BEFORE_PATH_RESULTS. Blind adjudication is pending.

## 1. Frozen input and scope

This is a deterministic description of the Frozen State9 output stream. It adds no market State and recalculates no State9 classification, M0, U, or threshold.

| Identity | SHA256 |
|---|---|
| RC2 Contract | 45859122a62ccdc946b31bb5709f3fc080ea4a4f935958afd8f1ca895f75b6ff |
| profile | 77ee61ba1808a2c17614439fe7d14212a53cbfa7358c032ce16989eeb5248922 |
| source snapshot | 08e1a20a4d022a1429b74387169dd8729a2eaeb4dc0008f3af2b52ec0e661c23 |
| M0 | 08cad3ca8316ccab644872e3d843e2d491ac6a953a03193d5c391be3bcf73bb3 |

The 9 formal Primary values are RISE, SHARP_RISE, RISE_STOP, PULLBACK, RANGE, REBOUND, DROP, SHARP_DROP, DROP_STOP. Null is not a State. The parent semantic Candidate, context reset adjudication, representation scope and C016–C027 provenance limitation remain in force. Neither observed endpoints nor transitions imply subsequent direction, prediction, safety, trading suitability or profit.

## 2. Endpoint input and time

Each input row is one saved Frozen State9 response plus its original scheduled slot. Required source properties: as_of, primary, current_semantics_observed, activity, basis, observed_at, context, leg_direction, direction_basis, fast_flag, fast_applicable_to_primary, stop, balance, events, numeric_status, rejection_reason, bar_metadata. The slot supplies scheduled_t, bar_end, row_status, auction. Numeric values and nested State9 metadata are copied without transformation.

scheduled_t is an integer, excluding bool, strictly increasing. bar_end is a timezone-aware ISO timestamp, strictly increasing in actual time. No duplicate or reordered row is sorted, merged, overwritten or backfilled. An invalid call is rejected before mutation. as_of equals scheduled_t. An observed row has a valid 9-State Primary, OBSERVED_FRESH or OBSERVED_NEW_SEGMENT_ONLY basis, non-INITIALIZING activity, numeric_status ACCEPTED and observed_at=scheduled_t. A non-observed row always has formal Primary_or_null=null. Its inherited display_primary and observed_at may refer to history, and are preserved separately. An observed_at later than scheduled_t is rejected.

Each result endpoint retains scheduled_t, bar_end, causal_segment_id, Primary_or_null, display_primary, current_semantics_observed, activity, basis, observed_at, local_direction, context_direction, direction_basis, fast, fast_applicable_to_primary, Stop/Range metadata, source events and quality/reset reason. Directions are -1, 0, +1 or null, with 0 meaning NONE where applicable. No inference from the visual FULL trend replaces these values.

## 3. Causal segment adapter

The candidate and reference derive segments independently from their respective saved Frozen traces and original slot metadata. No common State9 or Path state/helper is imported.

Segment ordinal is 0 before the first accepted bar. The first accepted row starts segment 1. A later accepted row starts a new segment if ANY applies: a prior unavailable/rejected row requires restart; scheduled_t differs from previous accepted t+1; source differs; auction differs; or the saved State9 row explicitly contains SEGMENT_RESET_NO_GAP_RETURN. Multiple causes create one new segment and are all recorded in a fixed order: AFTER_UNAVAILABLE, AFTER_REJECTED, ORDINAL_GAP, SOURCE_CHANGE, AUCTION_CHANGE, FROZEN_RESET_EVENT. The first accepted row records INITIAL_SEGMENT, plus any pending unavailable/rejected causes, without a SEGMENT_BREAK to a nonexistent accepted segment.

Non-accepted rows do not create an accepted causal segment, do not update previous accepted metadata, and set a restart requirement. They retain the current segment ID, or segment 0 before the first acceptance. Accepted INITIALIZING rows do belong to the accepted segment, but break observed continuity. An ordinal gap between any consecutive supplied endpoint rows also breaks observed continuity, even while unavailable. Segment IDs are case-local <case_id>:S0000, S0001, ...; streams from different cases or sessions are never connected.

## 4. Runs, ENTER, EXIT, HOLD and TRANSITION

An observed run is the maximal consecutive supplied endpoint sequence with all rows observed, identical Primary, identical causal_segment_id and scheduled_t advancing by exactly 1. It ends on a Primary change, non-observation, a new segment, or a missing ordinal. An adjacent pair is a valid observed connection ONLY when both rows are observed, in the same segment, and t advances by 1.

For a valid observed connection A→B: if A=B, emit HOLD, extend the existing run, and count no State change. If A differs from B, emit EXIT(A), TRANSITION(A,B), ENTER(B), all at B's scheduled_t/bar_end. The old run's last_observed_at remains A's last observation. The transition boundary is the confirmation time of B, not a pivot extremum or a retrospective market turning time.

At any other first observed endpoint, emit ENTER with from_primary_or_null=null, and OBSERVATION_RESUMED (reason FIRST_OBSERVATION, AFTER_NULL, or AFTER_SEGMENT_BREAK as applicable). This is not a Primary transition from null. EXIT due to loss/reset records a reason and to_primary_or_null=null, but is not a State-to-State transition. A→null→B never becomes A→B, including A=B. A new segment containing the same Primary also starts a new run, with no cross-segment HOLD or transition.

There is no invented EXIT at the supplied asOf. The last run is open/right-censored. A later observation may close it in a longer prefix, but must not revise earlier endpoint snapshots or events.

## 5. Quality events and ordering

SEGMENT_BREAK is emitted once at a supplied row when its segment ID changes from a previously started accepted segment, or the scheduled ordinal is nonconsecutive. It contains all reset causes, old/new segment IDs, and does not connect old/new Primary. There is no segment break solely because an accepted INITIALIZING row appears.

OBSERVATION_LOST is emitted when an observed previous supplied row is followed by a non-observed row. INITIALIZING is emitted on entry into accepted activity INITIALIZING, including the first row and a new segment. Repeated INITIALIZING does not generate repeated initialization entries. OBSERVATION_RESUMED accompanies a new observed run whose preceding endpoint was absent, null or separated by a break. These are quality events, not market States.

Per row, event order is fixed: SEGMENT_BREAK; OBSERVATION_LOST; INITIALIZING; closure EXIT; OBSERVATION_RESUMED; Primary TRANSITION; ENTER or HOLD; facet events in the order defined below. Global event IDs are deterministic case-local E000001, E000002, ... . Every event has t, bar_end, segment ID, from/to formal Primary or null, reason, and optional run/facet details. Loss plus later reset may generate two quality events for two distinct boundaries; never collapse them into a synthetic market transition.

## 6. Dwell duration

At the first observed endpoint, dwell_scheduled_bars=dwell_observed_bars=1. For a HOLD connection, increase observed count by 1; scheduled count=t-entered_t+1. Because continuity is mandatory, these counts agree. Store entered_at (scheduled ordinal), entered_bar_end, last_observed_at, last_observed_bar_end. Null/reset/gap contributes zero to a run and cannot be accumulated across runs. Duration is a count of scheduled bars with observed endpoints, not elapsed wall-clock minutes or a prediction of future duration.

Closed run records contain their last actual observation and closed_at/closed_reason at the next supplied boundary. Open runs have closed_at=null, closed_reason=null. Endpoint duration snapshots are immutable under extension of the prefix. No duration is published for a null endpoint.

## 7. Metadata/facet events

Facets are copied from Frozen State9, not independently classified. Compare facets only for valid observed connections. RANGE_ENTER/EXIT use activity BALANCED. STOP_ENTER/EXIT use STOPPED and the recognition identity (direction, center, recognized_at); a changed identity can exit and enter even if the Primary remains unchanged. STOP_UPDATE records changed Stop metadata within one identity. FAST_ENTER/EXIT records movement into/out of fast=true. FAST_AVAILABLE/UNAVAILABLE separately records null/non-null availability. Fast does not override Stop/Range/PULLBACK/REBOUND.

CONTEXT_CHANGE, LOCAL_DIRECTION_CHANGE and DIRECTION_BASIS_CHANGE record exact changes of their respective copied fields. A Range context retirement is shown as context NONE when the Frozen input says so; the Path builder never resurrects earlier context. Facet termination due to observation loss or segment reset is represented by the run/quality closure, not a new price-derived facet claim. Initial ENTER carries the complete current facet snapshot but no invented preceding facet transition.

## 8. Synthetic audit interpretation

Hand-authored Frozen-output-shaped fixtures audit the Path API and aggregation rules. They are not a proof that every arbitrary alphabet edge is reachable from actual Frozen State9 OHLC. No old State9 engine/suite is executed. Named fixtures cover all nine ENTER/EXIT and HOLD, null/initialization, gap/source/auction/rejection/reset, required directional families, Range/Stop/fast/context metadata, ordering rejection, replay and every prefix. Contract-expected events/durations are fixed before builders run. Do not label an ungenerated or unobserved edge PASS, or edit fixtures/expected meaning to fit results. Maximum192 streams, maximum64 endpoints/stream, total maximum12288 accepted fixture endpoints, plus a fixed set of invalid-input probes. No exhaustive 81-edge forcing or State9 modification.

## 9. Market scope, denominator and selection fixed in advance

Reuse the 29 existing Development case prefixes C001–C029 and saved candidate/independent traces from the parent final archive. Each is processed in isolation up to its existing historical asOf. New provider requests, new raw, new sessions, new sample draws and State9 reruns are zero in this stage. Retain old Exposure, 16 FAIL, 88-workflow incident, all consumed budgets and unknown historical usage.

Audit all29 reused case streams. Report case-row counts separately from distinct (security_id,session_id,scheduled_t) endpoints. Verify overlaps agree excluding case-local IDs; do not concatenate prefixes or count overlapping endpoints as independent observations. Market coverage denominators are case count and distinct security/session count, never a probability, future performance or population frequency.

PUBLIC candidate pool: select the longest existing prefix per security/session, by scheduled slot N, tie original case ID ascending. At most12 PUBLIC cases, at mostone per security/session, no new asOf and no redraw. Mechanically cover available features from ENTER/HOLD/TRANSITION, NULL_TO_OBSERVED, OBSERVED_TO_NULL, SEGMENT_BREAK, INITIALIZING, RANGE_ENTER/EXIT, STOP_ENTER/EXIT, FAST_ENTER/EXIT, CONTEXT_CHANGE, CONTEXT_NONE_AFTER_RANGE, DIRECTION_BASIS_CHANGE, DURATION and the9 observed Primary values. At each step pick the candidate with the greatest count of newly covered features, tie by SHA256(UTF8("STATE_PATH_PUBLIC_V1_20261002\n"+original_case_id)) ascending, then original ID. Stop if no new feature is covered or12 cases are selected. Unsupported/unobserved features stay NOT_OBSERVED, never filled using a different threshold or new data. Assign neutral P001... in the same hash order. The selection uses saved Path events mechanically; no human success rating, future outcome or reviewer answer enters selection. Save exact rule, pool, feature membership and mapping PRIVATE.

## 10. PUBLIC and representation

To obey the prohibition on Ark's Path answer key and reference output, PUBLIC has neutral FULL/LOCAL price charts and aligned **unfilled** Primary/observed/context/duration lanes, an endpoint worksheet and an event-timestamp worksheet containing all scheduled times. Reviewer independently fills these lanes/tables. All case-specific Primary labels, durations, transition names, chosen target names and candidate/reference traces are PRIVATE. PRIVATE contains the fully annotated price/Path charts and answers. An empty reviewer field means UNANSWERED, not formal null. This interpretation is fixed before results and prevents contradictory blind disclosure. It is not a claim that an Ark-labelled Path can be shown while remaining answer-blind.

LOCAL is the final40 scheduled endpoints up to the existing asOf, or the whole prefix if shorter. FULL contains only that case's prefix. Price limits use only displayed prefix prices, with5% of displayed high-low span padding (minimum display pad max(1e-6,abs(lastClose)*1e-6)); no other case or suffix controls the y-axis. Axis intervals and time labels use the displayed original bar_end slots. State9 names must appear with observed/null, activity, basis, observed_at and local/context/direction_basis/duration information in PRIVATE and reviewer completed answers. Provide the frozen representation notes and inherited limitations in PUBLIC. Raw known_at UNKNOWN and assumed availability bar_end remain separate. No artificial actual receipt chronology.

## 11. Coverage and stop gate

Coverage enumerates all9×9 Primary pairs: diagonals HOLD, off-diagonals TRANSITION; counts zero where absent. Add null-related quality and facet-event rows actually generated. synthetic_covered records only Path fixture coverage, not State9 market reachability. market_covered records saved prefix evidence. reviewer_case_available records material availability, not a received/reproduced review. No logical unreachable claims are made without a separate Contract proof.

Candidate/reference mismatch, frozen identity mismatch, decisive semantic contradiction, failed future isolation, required protected data or required Frozen change is STOP with evidence preservation. Technical I/O/render repairs do not change semantics or expected answers. Once PUBLIC is complete and separation inspected, status is STATE_PATH_REVIEW_PACKAGE_READY_AWAITING_RESPONSES. Work must not create independent reviewer answers or declare STATE_PATH_SEMANTIC_FREEZE_CANDIDATE before those responses and separate adjudication.
