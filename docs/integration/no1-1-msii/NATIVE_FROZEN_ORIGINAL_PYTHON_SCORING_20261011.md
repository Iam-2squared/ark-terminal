# No.1.1 Frozen original model inference: byte-exact Python reuse

To avoid training or changing the Frozen No.1.1 model, the integration branch reuses EXACT PUBLIC GIT BLOBS of the original Capital V5 research core_features.py, preprocessing.py, staircase.py in frozen-native-code. No modifications to original code, feature list, model weights, PAVA, ML scoring or thresholds.

Authority: pinned commit 710656491be06235901b45c50a8b5cbd714ba4eb. Original Git blobs:
- core_features.py 685a7774ed96556b810aa23957d12fda8f9654ba
- preprocessing.py 29119e9d9e5ca880159289728c9391e17f8427ca
- staircase.py 6863b2dded50e4d0caa4e2d470619017fcf0b759

The READ ONLY no11_native_original_python_smoke.py imports the original unchanged NumPy inference and PAVA/ML functions. Offline selftest runs with a zero-coefficient *synthetic-only* model without any personal or original private training data. Optional private model smoke loads the ORIGINAL SHA256-pinned H2/H3/H5 24 model files from private-native-models (provided in a separate private ZIP only to the user), evaluates one synthetic feature vector per saved model, and applies unchanged frozen PAVA/ML for all eight blocks. It prints counts only, no private weights, saved training IDs, features or scores.

Prerequisites for actual local model smoke: a local Python environment with NumPy (original dependency), the private 24-file model bundle separately installed, and this integration checkout. No network fetch or live orders are performed. The original inference is invoked only on synthetic feature rows. This does NOT reconstruct real Selector, State9, live feature history, PIT source arrival times or Entry/EXIT decision events. Zero-cash READ ONLY development remains allowed, and there is no new manual trading approval.

The real-model and low-latency feature path must subsequently demonstrate that the original core_features.py inputs, including entry fill timing/price and connected State9 trace prefix, are available causally BEFORE the relevant decision; historical unavailable inputs must never be relabelled live. Excel RSS order permission remains OFF, productionReady false, no main/frozen changes.
