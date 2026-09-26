# G7 review-harness repair source manifest

The tested source is preserved in the conversation attachment `SOURCE_CODE.zip` and in `Phase57_G7_Review_Harness_Repair_20260922.zip`.

This repository record is a source-lock, not the ZIP bytes. The source archive contains exactly the three repair/test modules listed below, and must be verified before extracting/running it.

Source archive SHA-256: b4289e74074b5d6a17b107c6f876c535f30a348bcfba33103085d7cadcf1a9d3
Source archive Git blob (for byte verification): dc214ee0146994c35b0f05b4d63cade4566f6996

| File | SHA-256 |
|---|---|
| causal_card.py | 57f8133a8cc005e10e3e67bf0fa5190276a69885e57237d25a614e999906d36e |
| run_regression.py | 91d501d3cc7d70d183262c228f907f108fa50fc382fb9ee20911f4bc6bb33e73 |
| test_causal_card.py | 01177b896ddb022b6d37683253ce7079e8e7169616222f70a47da033cb616e5c |

Dependency: unchanged repository `docs/phase57-five-minute-entry-state/mechanical-v1/reference.py` at commit 9a764e27086bf6bb1133c304b73c0027d1275760, SHA-256 e57d41b1a9472fb0ed254895d956623a438557f540443c0bee14a6db8f2d8d3d. The full repair attachment also includes an exact copy of this dependency for offline reproduction.

No live/trading/model runner imports these repair modules. Tests are local, not repository-wide CI.
