# V3 isolated Capital / Ownership preflight — 2026-10-11

The Windows PC already proved V2/V3 same-time private parity with all eight categorical checks true. The PC candidate V3 runtime is 2.86 seconds vs V2 33.25 seconds. Only one position, zero order/execution records were present. These are not evidence of certification for partial fills or the actual broker arrival time.

This step exercises the exact existing READ ONLY Capital/Ownership Gate on a new V3 capture, without changing the formal capture. It uses the repo-tracked original PC-tested V3 candidate (SHA256 pinned), the unchanged Ownership baseline from LOCALAPPDATA, the immutable Frozen No.1.1 HEAD, and the existing mutex. No older V2 snapshots, timestamps or account data are rewritten.

Run after updating the integration worktree, with MarketSpeed II and Excel workbook opened and RSS orders OFF:

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\ArkTerminal\no11-launcher\integration\no1-1-msii\windows\Test-No11V3CapitalReadOnly.ps1"

Expected NO11_V3_CAPITAL_STATUS=READ_ONLY_CAPITAL_PREVIEW and NO11_V3_CAPITAL_DIAGNOSTIC_PASS=True. Errors print sanitized uppercase labels only, not positions, symbols, quantities, cash values or private files.

The 30s RSS freshness window is unchanged, and V3's stricter 25s capture bound still applies. A positive test is a **READ ONLY funding preview, not actualFeedTimestampCertified**, and cannot authorize broker/Excel order enable. The desktop one-click official capture remains SHA-pinned to V2 until this independent Gate is physically verified. Existing ownership, safety ledgers, Frozen and main are unchanged.


## 2026-10-11: Windows Git CRLF checkout identified

The user's first V3 Capital preflight stopped at `V3_CANDIDATE_HASH_MISMATCH` before running the Capital Gate. Cross-check: the original PC-tested candidate and the Git blob match exactly (`f8be4d704ebad539762471ba62476c32b02a65b1`), so the likely mismatch occurs during checkout on the Windows PC with Git `core.autocrlf` conversion (LF to CRLF). Git now pins **only** the V3 candidate path to `text eol=lf` in the repository root `.gitattributes`, without changing the candidate contents, V2, any launcher, Ownership, Excel or frozen research. The Windows 5.1 CI now checks the SHA256 of the actual post-checkout worktree file, not only the upstream blob. On the PC after pulling this attributes fix, explicitly restore *only that tracked candidate file* from the updated HEAD and repeat the original diagnostic. Don't bypass SHA checks, don't change the tested script, and don't reset a Safety latch.
