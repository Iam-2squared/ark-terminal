# Windows read-only connection corrections (2026-10-26)

User-side evidence: the account observer saved sequence 1 as OBSERVED, then its second Publish failed in the three-argument File.Replace call with an invalid-path exception. The close receipt recorded failed=true. The market follow-up retained only the first Node eval error line; it did not establish a market capture or a Shadow run. No private account rows are included here.

Changes:
- Pass System.Management.Automation.Language.NullString.Value to File.Replace, retaining the atomic replace, durable temporary write and failure cleanup. No delete-then-move fallback is used.
- Pass the C50 trading-day JavaScript via Node stdin instead of a Windows PowerShell 5.1 native -e argument. Adjust the date argument index from 1 to 2. Keep the existing calendar, trading-hours and capacity guards.
- Add real powershell.exe regression tests for the old failures, repeated UTF-8 replacement, locked-destination failure and subsequent recovery, and the actual C50 calendar block. These tests do not open Excel or connect to a broker.
- Add a finite read-only connection runner. It samples the existing account book three times, then the existing chart capture/import path four times. It captures stdout and stderr separately, preserving multiline errors and the actual child exit code. It never starts Shadow or trading and never enables orders. It optionally indexes names inside already known private source ZIPs without extracting or executing their contents.

The uploaded results found no bootstrap configuration within the searched locations/depth. This change does not invent a configuration, certify security evidence or claim that required models/inputs are deployed. Full input assembly, account freshness/attribution, real-model Shadow, same-run recovery and real-order validation remain unverified until separately evidenced. A successful connection-check return code only covers its account/market check, not those later items.

Verification: use the CI run for the exact commit. The authoring session could not start its local container and does not claim a local execution. Windows regression success is not physical Excel/RSS success.

References: Microsoft NullString API documentation, File.Replace documentation, PowerShell about_Parsing, and Node command-line stdin documentation. No Frozen strategy, original integration files, order transport, safety reset or model weights are changed.
