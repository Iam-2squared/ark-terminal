# No.1.1 / 2026-10-26 one-shot read-only end-to-end observer

Call this only once MarketSpeed II RSS is running during JPX cash hours, after GitHub update. Use PowerShell in the user's local Windows PC:

    powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\ArkTerminal\no12-launcher\research\no12-prebuy-causal-runtime-20261011\windows\Run-No11Chart50ReadOnlyE2E.ps1 -Samples 4

The wrapper generates today's G1 PASS to Chart50 private plan from the saved 2026-10-23 daily archive, verifies original Ark Excel process and two workbook identities, reserves chart 50 cap, creates **temporary unsaved** Excel, captures four one-minute spaced market cumulative / chart1M observations, closes temporary workbook, imports byte-verified private snapshot files through the RSS approximation adapter, and prints ONLY aggregate counts and local receipt paths.

If there are private existing held/Watch/pending chart reservations, supply a pinned contract with `-PinsFile C:\...\private-pins.json`. Without it, the result is capacity shadow test ONLY, not live portfolio-aware operation. It never reads account VALUES and never changes any original workbook, model weights or orders.

Expected output includes `NO11_C50_CAPTURE=READ_ONLY_COMPLETE`, `NO11_CHART50_APPROX_VA_ROWS=...`, `NO11_C50_E2E_READONLY=COMPLETE_NOT_SELECTOR_NOT_TRADING`, `ORDER_TRANSMISSION=False`. If any gate fails, leave its exact ERROR code for engineering diagnosis; do not bypass.

Do not upload private files with stock prices/holdings; aggregate console output is sufficient. Neither this one-click probe nor the RSS per-minute Va proxy completes native P1/H235 model dispatch, Capital/EXIT/account execution, or real broker order reconciliation. 2026-10-27 live trading needs separate full-system physical gates. NEVER flip orderTransmission on the basis of this test.

Only four snapshots means a short integration diagnostic, not all-day production capture. No background monitoring is launched by this task.
