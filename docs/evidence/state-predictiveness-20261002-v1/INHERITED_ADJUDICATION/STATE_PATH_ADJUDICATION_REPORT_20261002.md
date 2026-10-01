# 🧭 Ark Terminal — State Path Blind Adjudication

**JST:** 2026-10-02T08:23:16+09:00  
**Status:** `STATE_PATH_SEMANTIC_FREEZE_CANDIDATE`  
**Final freeze:** not declared; this is a semantic freeze candidate.

## ✅ Blind integrity

- Reviewer status: `COMPLETED_PUBLIC_ONLY_BLIND_REVIEW`
- PRIVATE / Ark Path answer key / future / other reviewer answer seen before first-answer fixation: **false**
- First-answer canonical SHA256: `b37443eff20c44138049453832563765cd3cb387cd997092d9ab279212b1b88a`
- Recanonicalization identity: **PASS**
- Path Contract SHA256: `fc3808cb7d3d161e85527d7ebf97f902df7f0c3463457beddf1a25d053cee268`

## 📊 Adjudication

| Comparison | Agreement |
|---|---:|
| Primary / formal null | **302 / 302** |
| `current_semantics_observed` | **302 / 302** |
| causal segment ordinal | **302 / 302** |
| endpoint dwell / entered / last-observed boundaries | **302 / 302** |
| event type + time + from/to + segment | **609 / 609** |
| run Primary + entry/last + dwell + close boundary | **91 / 91** |
| Blind boundary concerns | **0** |
| Blind duration concerns | **0** |
| Blind null/reset concerns | **0** |

The Blind reconstruction and Designer PRIVATE agree on the **Path-defining semantics**: formal State/null, observed continuity, segment breaks, transitions, run boundaries and inclusive dwell.

## ⚠️ Nonblocking representation differences

The Blind reviewer used several reviewer-local or underspecified serialization choices. These are preserved rather than silently rewritten.

| Difference | Rows |
|---|---:|
| basis token lexical/provenance differences | **279** |
| └ observed rows within that | **241** |
| `fast_applicable_to_primary` interpretation on observed PULLBACK/REBOUND | **44** |
| non-observed carried facet serialization | **23** |
| event reason wording differences | **413** |

These differences did **not** move a Primary/null boundary, transition, segment, dwell, or run closure. The authoritative Frozen State9/PRIVATE tokens remain controlling downstream; reviewer-local normalization must not overwrite them.

## 🔒 Adjudication

No decisive Path semantic contradiction was found. No State9/Profile/M0/Path meaning, threshold, fixture or selection rule needs result-driven modification.

Therefore the correct next state is:

`STATE_PATH_SEMANTIC_FREEZE_CANDIDATE`

The inherited limitations remain explicit: actual receive `known_at` is unknown; `bar_end` availability is assumed for research; M0 finite precision is not a mathematical log-error proof or feed/U certification; C016–C027 provenance remains nonblocking; S/A/B/C, Membership and velocity remain non-core and incomplete.

## 🚀 Next

Start a **separate Predictiveness Contract / Precommit**. Only after its target, horizons, splits, leakage rules, metrics and finite budget are fixed may future observations be used as labels/evaluation. State9 and State Path stay frozen during that work.
