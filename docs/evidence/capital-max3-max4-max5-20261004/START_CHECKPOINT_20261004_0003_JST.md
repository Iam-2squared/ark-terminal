# Ark Terminal — Capital MAX3/MAX4/MAX5 Start Checkpoint

**Timestamp:** 2026-10-04 00:03 JST  
**Repo:** `Iam-2squared/ark-terminal`  
**Working branch:** `capital-max3-max4-max5-20261004`  
**Basis HEAD:** `1ecbcc43f75279fa302f19fd896add2aac15b537`

## Current verified position

- Source branch `exit-v3-freeze-reentry-v1-20261003` is identical to basis HEAD `1ecbcc43f75279fa302f19fd896add2aac15b537`.
- FIRST ENTRY v2 P1_Q70 remains OFFICIAL FREEZE at `4a2d6f35946b16820a13449a9288a6685a5c283c`.
- State9 Structural EXIT v3 Local Guard remains the adopted OFFICIAL FREEZE at `c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad`.
- EXIT v4 Recovery Failure remains rejected: `V4_NOT_BETTER_KEEP_V3`.
- Re-entry v1 remains Evidence-only and is NOT part of the integrated version.
- No existing branch matching MAX3 / MAX4 / MAX5 Capital first-pass was found before this branch was created.

## Immediate scope

Run the first Capital comparison using exactly:

`Frozen FIRST ENTRY v2 P1_Q70 + Frozen EXIT v3 Local Guard + NO Re-entry`

Compare only:

- MAX3 simultaneous positions
- MAX4 simultaneous positions
- MAX5 simultaneous positions

Reuse compatible existing causal portfolio infrastructure instead of rebuilding accounting from scratch.

## Required safeguards

Do not:

- rerun or redesign frozen Entry/EXIT research;
- include Re-entry v1 or EXIT v4;
- use future Entry→High / Selector→High / realized-return ranking as Capital decision inputs;
- open a broad Capital parameter search before the MAX3/MAX4/MAX5 result;
- reintroduce SHORT, margin, leverage, live orders, broker/Excel/RSS writes, paper trading, auto promotion, or production update.

Safety remains research-only and locked.

## Operating policy from this checkpoint onward

1. Before repeating older work, inspect GitHub and existing Evidence first.
2. Prefer the shortest valid path to the integrated version; avoid side research unless a genuine integrity blocker exists.
3. Do not trade audit quality for speed.
4. Use Claude only when a genuinely useful independent external review is needed.
5. At each meaningful checkpoint, persist:
   - current status,
   - next direction,
   - JST date/time,
   - relevant HEAD / evidence identity.
6. Numerical summaries should use clear tables and charts when they materially improve understanding.

## Next action

Locate the existing compatible Lane-C / capital simulator and frozen current Entry/EXIT artifacts, then adapt only what is necessary for a causal MAX3/MAX4/MAX5 replay. Produce evidence-ready comparison and stop for selection before any wider search.
