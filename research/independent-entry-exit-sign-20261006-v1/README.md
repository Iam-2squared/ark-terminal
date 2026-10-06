# Independent Entry→EXIT Sign V1

This module predicts PLUS/MINUS for the fixed Entry and fixed EXIT/EOD net result.
It imports no Capital engine. All teachers are equally weighted sign labels.
Old RNEG and stage1 model/OOF artifacts remain unchanged.

The research stages are prepare_inputs.py, run_study.py discovery, candidate
lock with GitHub actual GET readback, run_study.py late, and
run_study.py ablation. FIT excludes the latest five PAST sessions; CAL fixes
the threshold, and the same fitted model forecasts the next TEST block.
No CAL refit or TEST threshold update occurs.

inference.predict_sign(snapshot, model_artifact, threshold_artifact) returns
the sign score and research PASS/REJECT action. load_artifacts loads this
cycle's verified model/threshold files. Numeric/categorical keys must match
the model schema exactly; labels, return magnitudes, future EXIT and account
fields are not accepted.

Python/numpy/scipy/sklearn versions and every resolved estimator default are
recorded in MODEL_PRECOMMIT. Input and source hashes locate the unchanged
private archive. The package's runtime inputs, labels, row predictions and
models are private; GitHub holds code, aggregate counts and hash receipts.

The late interval is historically exposed Development. Neither partitioning
nor a precommit makes it Fresh/OOS. No deployment, Capital adapter, Replay,
second-layer training, full-data final fit, or upstream edit is included.
