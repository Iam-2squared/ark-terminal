# Phase57 P25 data-driven EXIT paired evaluation

Research-only evaluator for the causal data-driven EXIT scorer introduced in PR #431.

It reuses the exact P25 frozen evidence chain and evaluates only trades whose frozen membership includes `DYNAMIC_50`. Fixed-Horizon outcomes remain untouched and are paired by `sessionDate|entryTimestamp|symbol`. The data-driven EXIT consumes future bars sequentially after Entry; those bars are never used to alter Entry, model, universe, threshold, Dynamic-N, or fair-cutoff.

The current 2026-08-19..25 outcomes are not used to fit or tune the scorer. The analog pool comes only from the upstream pinned historical sessions, and the scorer itself independently enforces prior-session/fully-realized causal eligibility. Insufficient evidence defaults to HOLD.

This evaluator does not promote or execute anything. All broker/Excel/RSS/live/paper/promotion/production/transmission/fresh-holdout flags remain false.
