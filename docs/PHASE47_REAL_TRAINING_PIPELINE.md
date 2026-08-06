# Phase47 — Real Training Pipeline

Phase47 turns the Phase46 point-in-time dataset into review-only model candidates.

## Parts

1. Logistic Regression baseline
2. Deterministic Random Forest baseline
3. Deterministic Gradient Boosting baseline
4. Classification metrics: Accuracy, Precision, Recall, AUC and Brier Score
5. Trading metrics: Profit Factor, Sharpe, maximum drawdown, CAGR, net return and trade count
6. Strict chronological Walk Forward validation
7. Model ranking and review-only Candidate package
8. Local atomic-write CLI and regression tests

## Walk Forward

Each fold trains only on rows earlier than the test window. Random shuffling is not used. Fold metadata records training and test dates, sample counts and all evaluation metrics.

## Candidate governance

The selected model is only packaged as `CANDIDATE_REVIEW_ONLY`. It cannot promote itself, replace Production or change a broker account. The candidate includes dataset lineage, training period, feature names, Walk Forward results and a SHA-256 checksum.

## Local CLI

```powershell
node tools/run_phase47_training_pipeline.mjs `
  --input data/datasets/phase46-training-dataset.json `
  --output data/models/phase47-candidate.json
```

This process is local/CI-only and adds no Vercel Function or UI deployment.

## Safety

- broker writes: disabled
- Excel order writes: disabled
- MARKETSPEED II RSS order functions: disabled
- live trading: disabled
- automatic Candidate promotion: disabled
- Production updates: disabled
- human approval: required
