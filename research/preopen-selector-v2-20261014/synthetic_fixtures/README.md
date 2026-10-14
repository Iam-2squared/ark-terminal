# Synthetic fixtures

No market originals or model bytes are stored here.

The fixed matrix factory is ARK_V2_GENERATOR_20261014_V1 in model.py.
Its inputs are generated internally; caller rows, source files and seeds are not accepted.
Forecasts have a separately fixed factory fingerprint. Numerical-boundary fixtures use
short independently constructed Fraction histories in tests/test_required_matrix.py.
Optional-source fixtures and independent expected values are in test_additional_contracts.py.
Synthetic calendar identifiers and 2030 sessions are fictitious, never official JPX evidence.
The HGB matrix smoke validates engineering, not the predictive meaning of random generated features.
