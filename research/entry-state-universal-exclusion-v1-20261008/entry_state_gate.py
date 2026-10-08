"""Research-only candidate gate. No native No.1 code or production flags changed.

Apply to *every* original Frozen Entry event before V5 slot admission and allocation.
The caller supplies authoritative saved pre-buy State9 formal-primary evidence.
This module does not load any future path, labels, or exit outcome.
"""
from __future__ import annotations

from dataclasses import dataclass

BLOCK_STATES = frozenset(("PULLBACK", "SHARP_DROP"))
STATE9 = frozenset(("RISE_STOP", "RISE", "SHARP_RISE", "PULLBACK",
                    "RANGE", "REBOUND", "SHARP_DROP", "DROP", "DROP_STOP"))
KEEP_ACTIONS = frozenset(("KEEP", "KEEP_STATE_UNAVAILABLE"))


@dataclass(frozen=True)
class StateAtEntry:
    entry_id: str
    formal_primary: str | None
    state_usable: bool
    assumed_known_minute: int | None
    source_identity_ok: bool = True
    same_minute_phase_order_ok: bool = True


@dataclass(frozen=True)
class GateDecision:
    entry_id: str
    action: str
    reason: str


class ResearchEntryStateGate:
    def __init__(self):
        self.decisions_by_id: dict[str, GateDecision] = {}

    def decide(self, entry_id: str, entry_minute: int, evidence: StateAtEntry) -> GateDecision:
        # A canonical Frozen Entry event may not be offered a second time merely
        # because another position sold or cash was released.
        if entry_id in self.decisions_by_id:
            return GateDecision(entry_id, "SKIP_DUPLICATE", "ENTRY_ALREADY_EVALUATED")
        if not entry_id or entry_minute < 0 or not evidence.source_identity_ok or evidence.entry_id != entry_id:
            result = GateDecision(entry_id, "BLOCKED", "ENTRY_STATE_IDENTITY_OR_CLOCK_MISMATCH")
        elif not evidence.state_usable:
            result = GateDecision(entry_id, "KEEP_STATE_UNAVAILABLE", "NO_USABLE_FORMAL_STATE_AT_ENTRY")
        elif evidence.assumed_known_minute is None or evidence.assumed_known_minute > entry_minute:
            result = GateDecision(entry_id, "BLOCKED", "STATE_FROM_FUTURE_OR_UNKNOWN_CLOCK")
        elif evidence.assumed_known_minute == entry_minute and not evidence.same_minute_phase_order_ok:
            result = GateDecision(entry_id, "BLOCKED", "SAME_MINUTE_ORDER_NOT_ESTABLISHED")
        elif evidence.formal_primary not in STATE9:
            result = GateDecision(entry_id, "BLOCKED", "INVALID_FORMAL_PRIMARY")
        elif evidence.formal_primary in BLOCK_STATES:
            result = GateDecision(entry_id, "DROP", "EXCLUDED_FORMAL_PRIMARY_" + evidence.formal_primary)
        else:
            result = GateDecision(entry_id, "KEEP", "FORMAL_PRIMARY_NOT_EXCLUDED")
        self.decisions_by_id[entry_id] = result
        return result

    def filter_batch(self, candidates: list[dict], states: dict[str, StateAtEntry]) -> tuple[list[dict], list[GateDecision]]:
        """Run before V5 sorting/occupancy/reservation in every native Entry batch.

        The returned rows retain original order; native V5 remains sole allocator.
        Caller must stop an evaluation on BLOCKED. No native backfill is performed.
        """
        decisions: list[GateDecision] = []
        accepted: list[dict] = []
        for candidate in candidates:
            entry_id = candidate["entry_id"]
            evidence = states.get(entry_id)
            if evidence is None:
                decision = GateDecision(entry_id, "BLOCKED", "NO_STATE_EVIDENCE_ROW")
                self.decisions_by_id[entry_id] = decision
            else:
                decision = self.decide(entry_id, int(candidate["entry_minute"]), evidence)
            decisions.append(decision)
            if decision.action == "BLOCKED":
                raise ValueError(f"RESEARCH_GATE_BLOCKED: {entry_id}: {decision.reason}")
            if decision.action in KEEP_ACTIONS:
                accepted.append(candidate)
        return accepted, decisions
