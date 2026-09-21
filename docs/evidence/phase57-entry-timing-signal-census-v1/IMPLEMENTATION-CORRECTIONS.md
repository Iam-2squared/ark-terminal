# Evaluation boundary correction — no signal or policy change

During source-anatomy reconciliation after initial measurement, the initial
evaluator included an endpoint-stamped 11:30 auction bar when Selector time was
11:30. That bar is already closed at selection and is not a future low. The
archived source reader already distinguishes endpoint-stamped auction records
from regular bar-start timestamps. The evaluator now excludes an auction record
whose endpoint equals selection time. The session close is 15:00 before
2024-11-05 and 15:30 thereafter; 15:00 remains a regular bar in the latter period.

This is a clock-interpretation bug fix, not a new candidate, threshold, wait time,
cohort, signal, training target, execution price or horizon policy. Original
PROTOCOL.md and protocol.json are unchanged. The initial evaluator summaries and
manifest are retained in validation/evaluation-boundary-before; final primary
outputs use the corrected endpoint convention. Causal detectors and all six
trade streams are unchanged. Only ordered-oracle, retention and future path
anatomy are recomputed. Both initial full census regenerations and both corrected
evaluations are hash-compared; every minute-census file must remain byte-identical.

The correction reproduces the user's existing Low -> Later High counts exactly:
1%=1,895; 2%=1,504; 3%=1,143; 4%=854; 5%=666; 10%=229. This reconciliation
does not turn oracle range into realized profit. Selector->High counts remain
1,496 / 1,054 / 761 / 544 / 408 / 141; below1%=596, unavailable=63 separately.

Initial counts (before endpoint correction) were 1,897 / 1,507 / 1,146 / 856 /
670 / 231. They are superseded, not silently overwritten. No thresholds were
searched or changed after outcomes were observed.
