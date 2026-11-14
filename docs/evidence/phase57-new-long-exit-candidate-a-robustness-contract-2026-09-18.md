# Phase57 NEW LONG EXIT Candidate A — Robustness / Freeze Audit Contract

Date: 2026-09-18 JST
Status: **CANDIDATE_LOGIC_FROZEN**

No Candidate A logic changes are allowed in this audit.

## Audit gates

1. Chronological stability:
   - for each cohort separately, Candidate A mean delta vs Fixed12 must be >=0 in at least 3 of 4 chronological session blocks.

2. Symbol concentration:
   - excluding the top 3 frequency symbols in each cohort, mean delta vs Fixed12 must remain >=0.

3. Adverse evaluator-only subsets:
   - cheaper-DIP D30 additional-drop >=2% (106 identities): Candidate A mean must be non-worse than Fixed12.
   - >=5% (21 identities): Candidate A mean must be non-worse than Fixed12.

4. Causal opportunity:
   - +3 preservation remains 100%;
   - +5 preservation remains >=90% in each cohort.

5. deterministic regeneration / safety / frozen upstream.

All pass -> `NEW_LONG_EXIT_CANDIDATE_A_DEVELOPMENT_FREEZE_READY`.
Any fail -> `NEW_LONG_EXIT_CANDIDATE_A_ROBUSTNESS_BLOCKED`.

A failure does not authorize threshold changes. Fresh/OOS remains sealed.
