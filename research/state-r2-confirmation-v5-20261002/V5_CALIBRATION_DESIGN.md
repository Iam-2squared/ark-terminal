# V5 calibration design

Method: `ROLLING_INNER_OOF_TEMPERATURE_V1`. One family only. V4 exposed Development is implementation research, never fresh confirmation or promotion.

Outer splits remain chronological. The inner split is fixed using outer-train calendar dates, not outcomes or class support. Retain the first five outer-train dates as initial inner warmup. Divide the remaining dates into four contiguous chronological blocks, with remainder dates assigned to earlier blocks. For each block, train on all outer-train dates strictly earlier than its start; purge target end at or after the validation-block start. Empty blocks remain explicit and are not refolded. The encoder is fit only on each inner train.

For R2, fit the unchanged weighted ridge/State9 base for alpha `[0.01, 0.1, 1]` on each evaluable inner block. Concatenate the rolling inner OOF predictions for each alpha. Select minimum uncalibrated date-equal logloss (equal dates, row mean within each date); exact numeric ties within `1e-12` choose larger alpha. Train weights remain V4 date-equal then security/session-equal, mean normalized to one. Alpha fallback is `0.1` if no inner OOF exists.

Using only the selected-alpha inner OOF predictions, choose temperature from `[0.5, 0.75, 1, 1.25, 1.5, 2]` by minimum date-equal logloss. Ties within `1e-12` prefer the value closest to 1, then larger T. Temperature selection requires at least two evaluable inner blocks, five distinct inner validation dates and twenty inner OOF rows; otherwise use T=1 and record the exact fallback reason. T=1 is a full candidate, not a forced correction.

R1 uses the unchanged current-Primary pseudo-count10 lookup, no alpha parameter; its inner rolling OOF and temperature selection use the same dates, purge, criterion, grid and fallback. After selections, refit once on the whole outer train and apply fixed T to outer test. Outer-test labels are never used for encoder, alpha or temperature.

REAL and TRUE_NULL use identical pipelines in fresh confirmation. No isotonic, Platt, vector scaling, neural calibration, new feature family or new threshold. R3 has no V5 fits; R4 no V5 fresh candidate fits. Preserve both raw and calibrated probabilities. Positive scalar T leaves argmax/hard predictions unchanged.

Research sanity scope: existing V4 CONTEXT_REVERSAL REAL R1/R2, original evaluable outer folds2 and3 only, original outer-test keys. Record raw/calibrated outer metrics and all inner artifacts. Research model fit maximum80; fresh model fit maximum160; combined cap240. No research bootstrap. A poor research outcome is retained without adding another method or adjusting this design.

Fresh sample scope, final split, source-code hashes and promotion rules will be frozen separately before any fresh label is generated. This design does not claim fresh scope has been acquired or that confirmation is complete.
