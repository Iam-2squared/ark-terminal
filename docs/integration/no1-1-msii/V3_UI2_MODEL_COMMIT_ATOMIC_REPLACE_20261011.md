# No.1.1 UI2 MODEL_COMMIT Windows filesystem repair, 2026-10-11

Windows screenshot shows RSS four status cells ready and V3 Capital/Ownership capture PASS, but UI model update fails with MODEL_COMMIT: the three-argument [IO.File]::Replace source, destination, NULL backup throws an invalid-path-form error in the existing-file update branch on this user's Windows PowerShell 5.1 PC.

This patch changes ONLY the READ ONLY UI model commit. It uses the verified private root, a UUID temporary JSON file, the exact approved ui-read-model.json destination, and an explicit non-null unique backup path on the same volume for File.Replace. It retains File.Move only for first creation. It rejects foreign private files, missing sources, unsafe filenames, reparse points, and directory collisions. The prior model is preserved if the replace fails; no non-atomic copy/delete fallback is used.

The Windows PowerShell 5.1 CI physically tests first creation, two successive replacements, denial of ownership-baseline target, and missing temporary source without any live brokerage/Excel access. Linux Node tests assert the relevant source invariants. No change to MarketSpeed II, Excel, account amounts, source timestamps, 30-second RSS gate, private Safety ledger, Frozen No.1.1 strategy, orders or main. Real Windows UI2 30-second recurring refresh requires user verification after CI passes.
