# No11 opening-source initialization finding — 2026-11-11

## Evidence interpretation

`NO11_BROKER_SOURCE_UNAVAILABLE` is raised by the native broker normalizer when
`brokerObservation.status` is not `OBSERVED`. An outer envelope marked
`OBSERVED` alone is insufficient: the nested broker observation may still be
`UNAVAILABLE`. A later successfully captured file does not reconstruct the
unavailable sample that the consumer actually read.

The registered-run initialization path resolves RSS opening funding before
constructing the broker ledger. Absence of its opening-funding receipt, broker
ledger, broker report, dispatch requests and dispatch results is consistent
with failure at this pre-ledger boundary. This is local filesystem evidence,
not an independent broker-side assertion that an entire account has no trades.

Do not describe the root cause as proven Excel disconnection, permanent
observer failure, or user terminal closure. The exact nested failure reason
at the failing instant was not retained in the supplied final snapshot.

## Candidate added (not installed)

`no11_rss_opening_source_wait.py` produces a derived funding module only from
normalized Git blob `7cc22baf4628f8163964742fb3a6ac1d6832413b`. The historical
funding source stays unchanged. The transform preserves Windows BOM/newlines.
It only replaces the first opening-observation acquisition and adds a helper;
receipt reuse, existing allocation, external-position exclusions and current
funding policy checks remain native.

The helper:

- Preserves a sanitized nested cause instead of collapsing every unavailable
  sample into a generic source error.
- Retries only explicit broker/account double-read changes and capture-duration
  failures. Generic/unclassified unavailability, identity changes, nonempty
  tails, schema/hash faults and other validation failures still block.
- Uses a monotonic retry budget (15 seconds by default, bounded at 60 seconds),
  a finite attempt cap and current session/cutoff/expiry checks during retries.
  The underlying read/normalizer keeps its own I/O timeout; this helper does not
  promise to preempt a blocking I/O call.
- Re-reads the source and runs the unchanged full native normalizer. It never
  substitutes a cached previously good sample or fabricates a successful read.
- Binds successful evidence to the approved Excel PID, precise process start
  and RSS key. An observer restart or nonadvancing successful sequence blocks.
- Performs no funding write, ledger mutation, order transmission or restart.
  Only the original resolver may persist a funding receipt after success.

The synthetic integration test uses the actual Node broker normalizer and
transformed Python resolver. It checks that personal holdings remain external,
only one opening receipt is written and no broker database is initialized.
Other tests cover timeouts, cutoff/date/expiry, clock reversal, source errors,
redaction, observer replacement, Excel restart including 100-ns start changes,
and preservation of native functions and Windows encodings.

## Remaining release gates

This is a candidate, not an installable LIVE recovery release. The PC runtime,
OneClick, configuration, original run records and claims have NOT been changed.
No prestart retry claim may be deleted or reused. No new fresh run may be
created under a date that already has a registered run merely because a ledger
file is absent.

The existing same-run rearm path expects an initialized ledger and reviewed
funding evidence; it is not automatically applicable to a pre-ledger failure.
A reviewed integration/installer and explicit session-specific approval remain
necessary before any future LIVE launch. A new day's session must use that
new day's data/configuration; yesterday's authorization must not be reused.

The newly added workflow is offline-only. CI success, when available, does not
certify behavior with the user's Excel, MarketSpeed II, account or live orders.
