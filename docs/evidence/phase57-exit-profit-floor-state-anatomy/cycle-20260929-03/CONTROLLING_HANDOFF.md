# Controlling handoff — 2026-09-29T21:33:12.666523+09:00

Status: `PATH_ANATOMY_INCOMPLETE_MAIN_INVALID`, basis HEAD `1e328c7b47acf6dc9341e784808f691cdbd75f18`, cycle `cycle-20260929-03`. Two previous INVALID cycles (`01`, `02`) remain untouched. The original precommit milestones and three diagnostic Floors remain unselected.

Input Gate PASS: 337,151 bar observations across IM/R1 entry paths, all float integer-equivalent timestamps, zero rejected, zero post-entry 0-bar. 1,385 incomplete continuous Entry and 20 missing exact 15:30 auction observations remain UNKNOWN. Full path known IM 102/819, R1 127/795 (funded subset IM 4/79, R1 2/32). Do not extrapolate known-path rates to all Entry.

Main ran once and independent ran once (mismatch 0 in its checked scope). **The full main remains INVALID**: Close giveback had 38 negative impossible rows of 904. Original `MAIN_SANITY_AUDIT.json` PASS was incomplete; `MAIN_SANITY_CORRECTION.json` controls. The independent audit did not recalculate Close giveback. High-based descriptive tables and independent counts are retained as bounded observations, not a completion or EXIT decision. Charts are diagnostic only.

Exposure: source is Outcome-exposed Development, inherited provenance PASS. Protected/Common Holdout/Validation/OOS/Fresh/Prospective opening, new provider, fit, EXIT/Capital Replay, orders, main merge all 0. Safety flags false. Input preflight 1, synthetic suite 1 (2 invocations disclosed), real schema preflight 1, main 1, independent 1; all finite real-data computation budgets consumed.

Next requires a new human-approved finite protocol. Correct nonnegative Close giveback definition and synthetic/Main Sanity negative-metric assertion, verify exact code hashes before any real-data run, then separately approve corrected Main and independent verification. No Floor/stop/P4 selection in this cycle.
