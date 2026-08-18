# Phase57 P25.3E — Prospective Trade-Pace Scorecard

P25.3E adds a descriptive daily scorecard on top of the lineage-pinned P25.3D evaluation. It does not change Entry, model, universe membership, horizon, cost assumptions, or any frozen OOS evidence.

The scorecard keeps the five precommitted variants in their fixed display order:

- `FIXED_5`
- `OLD_FIXED_30`
- `DYNAMIC_30`
- `DYNAMIC_40`
- `DYNAMIC_50`

For each variant it reports:

- expected operational trading sessions;
- common ready trading sessions;
- frozen Entry count and resolved Entry count;
- valid frozen Entries per trading session;
- observed Days-to-400 when actually reached;
- pace-estimated Days-to-400 before then;
- arithmetic pace checks for 400 trades in 30 trading days (13.333333 Entries/session) and 20 trading days (20 Entries/session);
- directional Hit Rate and after-cost Trade Win Rate separately;
- after-cost Net, Profit Factor, MaxDD and mean net return;
- coverage and denominator;
- same-time conservative effective independent Entries / independence ratio;
- session-equal-weight Net;
- symbol and sector concentration diagnostics.

The 30-day and 20-day pace lines are arithmetic reference targets only. They do not relax Entry or authorize model changes.

P25.3E does not rank variants, declare a winner, select Dynamic N from current outer OOS, promote a model, or consume the fresh holdout. Bad results stay visible.

Routine scorecard generation requires no MARKETSPEED II, Excel, board, Tick or Microstructure data. Those remain outside the current Day completion gate and MARKETSPEED is reserved for later milestone/final verification.

CI green validates code/workflow integrity only. The scorecard cannot make a performance claim until real prospective frozen-universe sessions and complete 5-minute data have accumulated.
