# Phase57 G7 Reviewer Prompt

Use this prompt in a **fresh review session** together with the blinded ZIP only.

## Instruction

You are Reviewer {{A_OR_B}} for Ark Terminal Phase57 State v2 G7 semantic falsification review.

You did not author the State v2 specification, have not seen the other reviewer's labels, and have not been given the sealed control key.

Open the supplied blinded ZIP and follow `INSTRUCTIONS.md`.

Review all 44 case images independently.

For each case, fill:
- caseId
- one or more allowed tags
- short rationale

Allowed tags:
- SEMANTICS_SUFFICIENT
- BOUNDARY_OR_TOLERANCE_SUSPECTED
- OBSERVATION_OR_PROVENANCE_PROBLEM
- VOCABULARY_GAP_CANDIDATE
- STATUS_SEMANTICS_PROBLEM
- INDETERMINATE

Use SEMANTICS_SUFFICIENT alone only if you see no semantic issue.

Do not:
- guess which cases are controls;
- use future prices or future outcomes;
- use PnL, Entry, EXIT, or profitability;
- search the symbol or infer company identity;
- change the State vocabulary or propose threshold tuning while scoring.

Return the completed CSV content in the exact `RESPONSE_TEMPLATE.csv` case order, followed by a concise summary:
- actual semantic concerns you found;
- any vocabulary-gap candidates;
- any observation/provenance concerns;
- confidence/limitations.

Freeze your labels before any comparison with another reviewer.
