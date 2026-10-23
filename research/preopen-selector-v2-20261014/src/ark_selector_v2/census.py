"""Private MODE B diagnostics; no input IO, fitting or evaluation-period access."""
from __future__ import annotations
from typing import Any
from .contracts import feature_names, LABEL_ID
from .exact_math import V2Error
from .labels import Label
from .native import NativeRows


def census_diagnostics(rows: NativeRows, teachers: dict[tuple[str, str, str], Label]) -> dict[str, Any]:
    if rows.role not in {"FIT", "CAL"}:
        raise V2Error("CENSUS_FIT_CAL_ONLY")
    if any(k[0] not in rows.sessions for k in teachers):
        raise V2Error("CENSUS_TEACHER_ROLE_LEAK")
    stages: dict[str, Any] = {}
    for stage in ("master", "price", "g0", "g1", "g2"):
        keys = {(r["session"], r["canonical_symbol"], r["market"]) for r in rows.layers[stage]}
        known = [teachers[k] for k in keys if k in teachers and teachers[k].status == "KNOWN"]
        raw = {str(k): sum(bool(l.raw_winner and l.raw_winner[k-1]) for l in known) for k in (1, 3, 5)}
        clean = {str(k): sum(bool(l.clean_winner and l.clean_winner[k-1]) for l in known) for k in (1, 3, 5)}
        loser = {str(k): sum(bool(l.raw_loser and l.raw_loser[i]) for l in known) for k, i in ((3, 2), (5, 3))}
        stages[stage] = {"N": len(keys), "knownN": len(known), "unknownN": len(keys)-len(known),
                         "raw_winner": raw, "clean_winner": clean, "raw_loser": loser}
    losses: dict[str, Any] = {}
    for base in ("master", "price", "g0"):
        losses[base] = {}
        for kind in ("raw_winner", "clean_winner"):
            losses[base][kind] = {}
            for k in (1, 3, 5):
                denominator = stages[base][kind][str(k)]
                lost = denominator-stages["g2"][kind][str(k)]
                losses[base][kind][str(k)] = {"lostN": lost, "baseline_known_hits": denominator,
                    "missed_rate": lost/denominator if denominator else None}
    observed = {}
    for name in feature_names():
        n = sum(r["values"][name] is not None for r in rows.rows)
        reasons: dict[str,int] = {}
        for r in rows.rows:
            if r["values"][name] is None:
                reason=r.get("missing_map",{}).get(name,"MISSING_REASON_NOT_SUPPLIED")
                reasons[reason]=reasons.get(reason,0)+1
        observed[name] = {"N": len(rows.rows), "observedN": n, "missingN": len(rows.rows)-n,
                          "observed_rate": n/len(rows.rows) if rows.rows else None,
                          "missing_rate": (len(rows.rows)-n)/len(rows.rows) if rows.rows else None,
                          "missing_reasons": reasons}
    g2keys={(r["session"],r["canonical_symbol"],r["market"]) for r in rows.rows}
    teacher_counts: dict[str,Any] = {}
    for head,classes in (("risk",range(3)),("opportunity_r0",range(6))):
        teacher_counts[head]={}
        for c in classes:
            class_keys=[k for k in g2keys if k in teachers and teachers[k].status=="KNOWN" and
                  (teachers[k].r==c if head=="risk" else teachers[k].r==0 and teachers[k].b==c)]
            teacher_counts[head][str(c)]={"rows":len(class_keys),"days":len({k[0] for k in class_keys}),
                                        "symbols":len({(k[1],k[2]) for k in class_keys})}
    oracle = None
    if rows.role == "FIT":
        oracle = {}
        for k in (3, 5):
            def hit(r: dict[str, Any]) -> bool:
                value = teachers.get((r["session"], r["canonical_symbol"], r["market"]))
                return bool(value is not None and value.clean_winner is not None and value.clean_winner[k-1])
            hits = [sum(hit(r) for r in rows.rows if r["session"] == d) for d in rows.sessions]
            oracle[str(k)] = sum(min(15, n) for n in hits)/len(rows.sessions) if rows.sessions else None
    return {"schema": "ARK_V2_PRIVATE_CENSUS_DIAGNOSTICS_V1", "role": rows.role,
            "label_id": LABEL_ID, "all_calendar_sessions": len(rows.sessions), "stages": stages,
            "big_winner_exclusions": losses, "features": observed, "fit_oracle_upper": oracle,
            "teacher_support_counts_before_admission": teacher_counts,
            "unknown_is_not_nonhit_teacher": True, "public_release_allowed": False,
            "market_fits": 0, "calibration_optimizations": 0}
