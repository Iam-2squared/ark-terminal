# Capital sign-only filter stage1

This is the frozen four-family, sign-only research cycle. It has no Capital engine, order or stage2 entry point.

Set ARK_SIGN_WORKSPACE to a work directory with the original RNEG package under reuse_sign/ and the permitted score authority recovered by its manifest. Git-backed source and aggregate evidence live in this directory and its matching docs/evidence folder. Private row artifacts live in capital_sign_only_private/.

Original source references are pinned in SOURCE_BINDING.json and the private archive PACKAGE_INPUT_REFERENCES.json. Restore the saved score producers/first OOF from the Quality v3 and Main handoff packages; fetch the exact producer-public receipts at their pinned GitHub heads. Never backscore missing warmup rows or fit those producers again.

Completed artifacts are for review and inference audit. Do not rerun fit_sign.py against the completed archive: its exclusive OOF_STARTED and prediction files deliberately reject duplicate runs. The 32 completed fitted models must remain the first attempts.

The original preparation sequence was build_sign_view.py -> prepare_inputs.py -> test_sign.py -> actual GitHub precommit/readback -> fit_sign.py -> actual OOF checkpoint/readback -> evaluate_sign.py -> audit_sign_view.py -> audit_sign.py -> audit_metrics_and_edges.py -> build_report.py.

Only build_sign_view.py and the independent teacher-boundary adapter audit_sign_view.py may read source debit/credit. Model requests, runtime thresholds, evaluation and gates accept the six-column sign view only; numerical purchase-time features remain allowed. Magnitude provenance hashes never enter training mathematics.

The recorded Primary is SF_D_UNION + alpha0.10 over all38 OOF sessions including OFF. Keep its failed negative-removal gate and do not switch to a different group or alpha after seeing results.

Runtime: Python3.12, numpy2.3.5, scikit-learn1.8.0, matplotlib3.10.8. No environment upgrades, extra fits, Capital/RESET20/Replacement Replay, upstream edits or production promotion are part of this cycle.
