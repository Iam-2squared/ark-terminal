# Next recovery draft — no real data run authorized

The executed `anatomy.py` is frozen by `RUN_INVALID_FLOAT_MINUTE.json`. The producer constructs `np.array(..., float)` and serializes `a.tolist()`, so an integral minute arrives as a float. A new precommitted parser should accept only finite numeric integral minute values in the scheduled set, normalize them to int, and reject booleans/fractional minutes. Both main and independent parsers need a synthetic end-to-end fixture using `540.0` and an auction endpoint.

Before any further real-data computation, independently inspect canonical session and auction metadata. The current code requires a 930 single-price row; actual source coverage is unassessed. Preserve missing bars as UNKNOWN and do not extend horizons or infer fills. Any new calculation requires a new finite approval; the current corrected main budget is exhausted.
