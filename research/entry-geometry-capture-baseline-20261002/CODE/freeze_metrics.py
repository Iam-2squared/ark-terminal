#!/usr/bin/env python3
"""Freeze definitions without reading/aggregating Geometry results."""
import json
from pathlib import Path
P=Path(__file__).resolve().parents[1]
contract={
 'document_id':'WORK_ENTRY_GEOMETRY_CAPTURE_BASELINE_20261002_V1',
 'status':'FROZEN_BEFORE_NEW_GEOMETRY_AGGREGATES','schema_version':1,
 'scope':'DESCRIPTIVE_SAVED_EVIDENCE_ONLY','arms':['IMMEDIATE','R1'],
 'population':'canonical2155 unique opportunity IDs; same full denominator for each arm',
 'price_basis':'Exact canonical selectorPrice; saved next-open+5bps Entry price, unadjusted JPY; no synthetic fills',
 'oracle_authorities':{
  'selector_to_high_pct':'saved selectorOutcome.mfeEnd is authoritative canonical Selector MFE; retains its inherited max(0,...) convention. Unclipped observed global-high return is separate diagnostic. Positive values match ratio to global High.',
  'global_low':'no saved global-low timestamp in canonical Entry records. Mechanically locate lowest LOW in saved canonical future raw rows, earliest tied bar; never replace orderedOracle.',
  'global_high':'mechanically locate highest HIGH, earliest tied bar, for chronology; saved canonical MFE remains authority for denominator and Winners.',
  'ordered_oracle':'preserve existing best strictly ordered Low->High rebound and Entry quality fields separately. It is neither Selector-global High nor necessarily global Low.',
  'entry_to_later_high_pct':'highest HIGH among saved future rows whose bar-start minute is strictly greater than Entry minute. Earliest tied bar. Saved ordered-high field reused only as legacy comparison; never pretend it always equals this maximum.',
 },
 'path_window':{
  'canonical_future_rows':'saved today bars at or after Selector minute, except endpoint-stamped auction at exact Selector minute690 or session close. Do not open next session. Use only saved source values.',
  'no_new_supplementation':True,
  'evaluable':'selectorOutcome.fullStatus AVAILABLE and orderedOracle.fullSessionEvaluable true; canonical inherited source-completeness admission, not proof every minute traded/observed',
  'partial':'preserve observed extrema as diagnostic but primary extrema metrics null if canonical full-session not evaluable',
  'intrabar':'STRICT_LATER_BAR high excludes Entry bar. Low==Entry minute convention uses <=, but same-bar true event ordering is unknown and labeled.',
 },
 'formulas':{
  'selector_to_high_pct':'canonical saved selectorOutcome.mfeEnd; audit against max(0,100*(GlobalHigh/SelectorPrice-1))',
  'selector_to_observed_global_high_unclipped_pct':'100*(GlobalHigh/SelectorPrice-1), diagnostic only',
  'entry_to_later_high_pct':'100*(LaterHighStrictlyAfterEntry/EntryPrice-1); no clipping',
  'upside_retention_pct':'100*entry_to_later_high_pct/selector_to_high_pct if denominator>0 and both known; no clipping',
  'low_to_entry_pct':'100*(EntryPrice/GlobalLow-1) ONLY when GlobalLowMinute<=EntryMinute',
  'entry_to_future_low_pct':'100*(GlobalLow/EntryPrice-1) ONLY when EntryMinute<GlobalLowMinute',
  'entry_mae_end_pct':'saved labels.maeEnd, signed pct; never filled unknown with0',
  'entry_mae_30_pct':'saved labels.30.MAE if present; its original COMPLETE/PARTIAL/CENSORED status preserved',
  'entry_mae_60_pct':'saved labels.60.MAE if present; original status preserved',
  'selector_to_entry_active_minutes':'active_ordinal(Entry)-active_ordinal(Selector)',
  'selector_to_entry_wall_minutes':'Entry clock minute - Selector clock minute',
  'entry_to_high_active_minutes':'active_ordinal(LaterHighStrictlyAfterEntry)-active_ordinal(Entry)',
  'entry_to_high_wall_minutes':'LaterHigh clock minute - Entry clock minute',
 },
 'ordering_status':['NO_ENTRY','LOW_UNKNOWN','LOW_AT_OR_BEFORE_ENTRY','LOW_AFTER_ENTRY'],
 'active_clock':{'timezone':'Asia/Tokyo','AM':[540,690],'PM':[750,930],
  'ordinal_AM':'minute-540','ordinal_PM':'150+minute-750','lunch_minutes_added':0,
  'outside':'null + OUTSIDE_ACTIVE_SESSION; unresolved source contradiction stops work'},
 'winner_capture':{
  'thresholds_pct':[1,2,3,5],'winner':'canonical saved selectorOutcome.mfeEnd >= level',
  'capture_authority':'saved Entry labels.mfeEnd (includes Entry bar under inherited canonical semantics), not newly fitted decisions',
  'classes':{'CAPTURED':'filled and saved Entry MFE >= level','NO_ENTRY':'no saved fill','ENTERED_BUT_BELOW_THRESHOLD':'filled, known Entry MFE < level','OUTCOME_UNKNOWN':'filled, null Entry MFE'},
  'known_missed':'NO_ENTRY+ENTERED_BUT_BELOW_THRESHOLD; OUTCOME_UNKNOWN kept separate',
  'legacy_missed':'existing scorecards count all not captured including unknown; preserved as legacy comparison only',
  'strict_later_sensitivity':'same Selector Winners, same4 classes using entry_to_later_high_pct; report canonical-vs-strict-later discrepancies, no label replacement',
  'selector_unknown':'not assigned to winner or nonwinner; separate count',
  'late_entry_attribution':'below-threshold rows with canonical GlobalHighMinute<=EntryMinute are chronology-associated; not proof of causal reason',
 },
 'buckets':{
  'selector_to_high_pct':{'edges':[1,3,5,10],'labels':['<1%','1–3%','3–5%','5–10%','>=10%'],'rule':'left closed, right open; <1 includes0'},
  'entry_to_later_high_pct':{'edges':[0,1,2,3,5],'labels':['<=0%','0–1%','1–2%','2–3%','3–5%','>=5%'],'rule':'first<=0; interior low<=x<high, exclude0 from second'},
  'low_to_entry_pct':{'edges':[0,.5,1,2,3],'labels':['<=0%','0–0.5%','0.5–1%','1–2%','2–3%','>=3%'],'rule':'first<=0; interior low<=x<high, exclude0 from second'},
  'selector_to_entry_active_minutes':{'edges':[0,5,10,20,30],'labels':['0m','1–5m','6–10m','11–20m','21–30m','>30m'],'rule':'integer active minutes;0 then right-closed intervals'},
  'entry_to_high_active_minutes':{'edges':[5,15,30,60],'labels':['<=5m','6–15m','16–30m','31–60m','>60m'],'rule':'integer active minutes; right-closed'},
 },
 'time_of_day_bands':{'09:00–10:00':[540,600],'10:00–11:00':[600,660],'11:00–11:30':[660,691],'12:30–14:00':[750,840],'14:00–15:00':[840,900],'15:00–15:30':[900,931]},
 'time_of_day_primary':'Selector timestamp so no-entry rows retain a band; Entry time band secondary',
 'continuous_summary':['N','known_N','unknown_N','mean','median','p5','p25','p75','p90','p95','min','max'],
 'quantile':'linear interpolation (Hyndman-Fan type7); no winsorization',
 'denominators':'primary N2155 per arm; per-fill known/unknown also report. Conditioned groups keep their own total_N. Arms are paired descriptive populations, not independent observations.',
 'missing_reasons':['NO_ENTRY','FULL_SESSION_NOT_EVALUABLE','NO_STRICTLY_LATER_HIGH','NONPOSITIVE_SELECTOR_UPSIDE','LOW_UNKNOWN','ORDERING_NOT_APPLICABLE','SAVED_LABEL_UNKNOWN','STATE9_IDENTITY_NOT_CERTIFIED'],
 'state_panel':'final RC2 State9 only on certified exact identity join. Legacy nine-pattern schema cannot substitute; NOT_AVAILABLE receipt allowed.',
 'audit':{'absolute_tolerance_pct':1e-8,'exact':'IDs, counts, clock minutes, categories, buckets','future_fields_decision_use':0},
 'interpretation_boundaries':['No significance/promotion Gate','No causal delay-effect inference from arm aggregates','No floor-perfect Entry target','No fitted/swept downside tolerance','No profit/EXIT/portfolio inference'],
 'forbidden_actuals':{'fit':0,'provider':0,'policy_replay':0,'bootstrap':0,'new_partition_open':0,'orders':0,'main_merge':0}
}
(P/'METRIC_CONTRACT.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
print('C2_METRIC_FREEZE_READY')
