# CI dependency correction — 2026-09-21

Research/evidence snapshot: 22cb6b6d9ada1fb430c6ea791307d4a2f973b2e8.
Dedicated new audit run 35556304305 failed before verification with
ModuleNotFoundError: scipy. The new workflow omitted an existing transitive dependency.
Add scipy==1.17.0, matching the original study workflow. No study code, thresholds,
features, evidence values or tests changed. The original completion receipt's workflow
hash identifies the workflow at 22cb6b6d; it is a historical pin, superseded only for
this dependency installation by this CI correction. Original study pins remain unchanged.

Original State Path Anatomy verification on 22cb6b6d succeeded (35556304182).
Separately, EXIT CC Freeze Audit 35556304206 failed its pre-existing freeze gate:
DIP_REPRICE_OPPORTUNITY_timeOrdered_plus5, contractLaterBarOrder, exactRoutedLedger.
Its verdict is NEW_LONG_EXIT_CANDIDATE_C_KILL / freezeAllowed=false.
This audit is outside the authorized Entry research; no EXIT changes or gate relaxation.
Dedicated Entry CI success must not be reported as PR-wide green.
