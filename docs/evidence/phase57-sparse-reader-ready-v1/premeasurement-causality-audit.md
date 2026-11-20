# Calibration origin audit — before measurement

Protocol SHA and all dates/thresholds remain unchanged.
Calendar-only inspection gives:

| Fold | Forecast origin | Target start | Target end |
|---|---|---|---|
| 1 | 2025-04-21 | 2025-04-30 | 2025-05-29 |
| 2 | 2025-05-22 | 2025-05-30 | 2025-06-26 |
| 3 | 2025-06-19 | 2025-06-27 | 2025-07-28 |

The fold1-fitted calibration mapping is unavailable at fold2's forecast origin.
Applying it there would be retrospective, despite the target windows not overlapping.
Implement an explicit artifact-availability guard: fold2 is NOT_AVAILABLE, fold3
may be diagnosed; the fixed requirement for TWO eligible independent periods cannot
pass in this schedule. Do not relax that requirement or select replacement dates.
Existing WATCH remains WATCH. This audit was made while CI run35482940549 was still
downloading artifacts, before restoration/collection/measurement began. The replacement
run supersedes that implementation and cancels the redundant run. Source data is unchanged.
