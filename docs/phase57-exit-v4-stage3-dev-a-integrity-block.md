# Stage 3 DEV-A historical measurement — integrity preflight

Gate: **DEV_A_MEASUREMENT_INTEGRITY_BLOCKED**

The authorized DEV-A measurement did not open market outcomes. A result-blind chronological preflight found that the frozen EXIT v3/v4 analog source cannot be used causally for the frozen DEV-A dates.

| Item | Frozen value |
|---|---|
| DEV-A | 70 sessions, 2024-09-10 through 2024-12-20 |
| Frozen analog source | P24 canonical Yahoo 5m byte snapshot |
| Analog source end | 2026-08-12T06:30:00.000Z |
| Canonical window | 56 calendar days |
| Earliest possible analog timestamp | 2026-06-17T06:30:00.000Z |
| Required causal neighbors | 30 |
| Maximum causal neighbors for any DEV-A decision | 0 |
| Safe treatment | Stop before outcome access |

The scorer requires both `analog.sessionDate < evaluated sessionDate` and `analog.fullyRealizedAt < decision timestamp`. Every possible frozen analog row postdates every DEV-A session. Forcing those rows into DEV-A would be a material point-in-time violation. Leaving the policy unchanged makes every v3/v4 base score not ready and causes a fail-closed HOLD to session end; equality with the Fixed arm would therefore be an implementation fallback, not evidence that v3/v4 performs equally.

## Measurement status

| Item | Result |
|---|---:|
| DEV-A sessions authorized | 70 |
| DEV-A sessions opened | 0 |
| First ENTER events measured | Not opened |
| Fixed outcomes | Not opened |
| EXIT v3 outcomes | Not opened |
| EXIT v4 outcomes | Not opened |
| PIT violations accepted | 0 |
| DEV-B / Validation / Holdout / OOS / Reserve access | 0 |
| Protected / Fresh access | 0 |

No performance result, threshold, feature, Entry behavior, EXIT policy, or allocation was changed.

## Frozen identifiers

| Item | SHA-256 |
|---|---|
| Tier 2 contract | `2aa9fd80596c0f71f2359fb132288a15d563e3fab8e22ecbac54fda308a54a70` |
| Stage 2 allocation contract | `7e2792dfe35998716535bbbe0c9347adf87c9d6179f004b405bf0afd7240faec` |
| Stage 2 allocation manifest | `316d65a051ef62a0917446a910eabd9c46f2b577486fb5ead5743c446075a276` |
| DEV-A date list | `8fc50ffaff4aa7107b5e1a904237c3ea4dba00dd4a27255c94839627363a9909` |
| EXIT v3 policy | `634514abac1ea1129ecf669e677d677a18378b1f75b7ba872bae781b82c401f2` |
| EXIT v4 policy | `2d512dd810d057807bc59a0138a3db98035e57ff2c23c186ba096beeb6be26cb` |
| Frozen analog snapshot | `10ec0b89893823f9e2f7ba720db2d0fad8e76d642fe00f7b77d387ae6be6b12a` |

## Required next decision

Before any outcome access, choose and freeze one result-blind repair:

1. provide a verified analog source whose labels are fully realized before 2024-09-10; or
2. conduct a separate methodology review and explicitly replace the frozen chronological allocation with an evaluation window after the analog history.

Neither repair is authorized or performed here. Stage 3 stops at the integrity gate.
