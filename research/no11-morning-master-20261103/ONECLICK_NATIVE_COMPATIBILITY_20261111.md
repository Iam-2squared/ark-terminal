# OneClick Display V2: preserved native status families

## Why the first deployment blocked

The first installer accepted only the normalized original status Git blob
`1f5611336abc8d68731a44243fa67a6c6a4ebf9f`. The observed installed status had
normalized blob `89034581d9ee797ba76151d62668184942bbad3f`. This was a
compatibility rejection before a display journal or launcher write, not proof
of file corruption.

## Independent provenance, not a caller-supplied whitelist

The reported status is reproduced from the repository original by applying
these existing published transforms to bytes in a synthetic test only:

1. `no11_update_path.transform('status', original)` adds the weekend Friday
   DATA-update availability branch.
2. `install_no11_completed_session_update.transform('status', previous)` adds
   DATA availability for the latest completed session.

`test_no11_oneclick_display_compatibility.py` asserts that the resulting
normalized Git blob equals the reported value. It separately compares every
function other than `inspect` with the original AST; the historical patches
modify DATA availability within `inspect`, not the source-evidence validators.
The original, either individual transform, and both combined are tested.

The runtime does NOT trust an arbitrary supplied hash or marker. Its common
`native_source_family` verifier removes only the exact two published spans in
memory, in reverse order, then requires every remaining normalized byte to
match the pinned original. Unknown comments, statements, literals, relocation,
duplicated markers, extra edits, and malformed spans remain rejected.
BOM/CRLF are handled as formatting variants. No reconstructed original is
written to the PC: the user's actual native file is retained byte-for-byte.

Installation and each normal display startup call the same verifier. The
installed contract also retains the raw SHA256 of the actual native file and
presenter. Changing even an otherwise supported native variant after installing
still invalidates that contract instead of silently changing authorization.

## Runtime semantics and preservation

The new presenter delegates to the preserved original `inspect` function and
adds `presentation` only. The regression suite compares all original returned
fields across four native families, four weekdays/weekend dates and seven time
windows, including when the DATA tool exists. Weekend DATA availability must
remain available where the original allows it, while the presentation still
identifies Saturday/Sunday as `NO SESSION`. No Trade permission is inferred
from DATA readiness.

The launcher migration handles the original display region and its exact
published historical pre-order-retry variant. In the latter case it preserves
the already-present `CanRetryPreorder` input, all Enabled expressions, the
existing date-limited function, and the full click-handler suffix. It neither
adds nor revives a retry route. The actual published selection-header patch is
included in tests. White-theme/customized bytes outside replacement spans
must round-trip exactly, including mixed line endings. Unknown display spans
remain blocked rather than guessed.

The complete locally styled launcher identified by the operator is not itself
assumed to match a repository launcher. Compatibility is checked by exact
scoped anchors and the full reverse-transform proof at installation. The
installer must retain the user's styling, not copy the repository theme.

## Deployment boundary

Use the immutable, hash-verified release directly from the operator's existing
interactive PowerShell. Do not execute the old outer named bootstrap wrapper,
remove process checks, delete claims or reset a journal to force installation.
The native status, broker/strategy/EXIT sources, schedules, settings, data,
reservations and trading records are not modification targets.

A successful display installation remains a software/readback result only.
It is not a broker acknowledgement, proof of live engine liveness, approval for
a future session, or evidence that the prior trading initialization fault has
been resolved on the real machine.
