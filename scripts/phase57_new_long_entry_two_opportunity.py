"""Pure research kernel for the frozen Phase57 NEW LONG Entry two-opportunity candidate.

No market provider, model, EXIT, Capital, Portfolio, order, broker, 1m, or outcome
imports. The kernel owns causal Entry state/opportunity emission only. It never
owns quantity/notional.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping

CONTRACT_STATUS = "NEW_LONG_ENTRY_TWO_OPPORTUNITY_CANDIDATE_FROZEN"
KERNEL_VERSION = "phase57-new-long-entry-two-opportunity-v1"

TERMINAL_SECONDARY_STATES = {
    "FIRST_BAR_CONTINUATION",
    "DIP_REPRICE_EMITTED",
    "SECONDARY_UNKNOWN",
    "SECONDARY_EXPIRED_BOUNDARY",
}


@dataclass(frozen=True)
class Anchor:
    anchor_id: str
    symbol: str
    session: str
    decision_timestamp: str
    decision_price: float

    def validate(self) -> None:
        if not self.anchor_id or not self.symbol or not self.session or not self.decision_timestamp:
            raise ValueError("INVALID_ANCHOR_IDENTITY")
        if not isinstance(self.decision_price, (int, float)) or isinstance(self.decision_price, bool) or self.decision_price <= 0:
            raise ValueError("INVALID_DECISION_PRICE")


@dataclass(frozen=True)
class EntryState:
    anchor: Anchor
    state: str
    secondary_terminal: bool


def _base(anchor: Anchor) -> dict[str, Any]:
    return {
        "kernelVersion": KERNEL_VERSION,
        "anchorId": anchor.anchor_id,
        "symbol": anchor.symbol,
        "session": anchor.session,
        "decisionTimestamp": anchor.decision_timestamp,
        "decisionPrice": float(anchor.decision_price),
    }


def emit_initial_opportunity(anchor: Anchor) -> tuple[EntryState, dict[str, Any]]:
    """Emit t0 opportunity without reading any post-selection market observation."""
    anchor.validate()
    event = {
        **_base(anchor),
        "eventType": "INITIAL_ENTRY_OPPORTUNITY",
        "sourceState": "SELECTOR_CANDIDATE",
        "opportunityTimestamp": anchor.decision_timestamp,
        "quantityOwnedByEntry": False,
    }
    return EntryState(anchor=anchor, state="INITIAL_ENTRY_OPPORTUNITY", secondary_terminal=False), event


def observe_first_completed_bar(
    state: EntryState,
    bar: Mapping[str, Any] | None,
    *,
    reference_bar: Mapping[str, Any] | None = None,
    boundary_expired: bool = False,
    reference_boundary_expired: bool = False,
) -> tuple[EntryState, dict[str, Any] | None]:
    """Perform the only post-t0 Entry transition.

    Decision fields consumed from the completed first bar are only `missing`,
    `close`/`c`, and `end`. If that close establishes FIRST_CLOSED_DIP, the
    secondary opportunity is emitted only when the causally contemporaneous
    next regular 5m OPEN reference is observable. From `reference_bar` only
    `missing`, `open`/`o`, and `start` are consumed. High/low/volume, later bars,
    and every evaluator outcome field are intentionally ignored.
    """
    if state.secondary_terminal or state.state != "INITIAL_ENTRY_OPPORTUNITY":
        raise ValueError("SECONDARY_STATE_ALREADY_TERMINAL")

    anchor = state.anchor
    if boundary_expired:
        return EntryState(anchor, "SECONDARY_EXPIRED_BOUNDARY", True), None

    if bar is None or bool(bar.get("missing", False)):
        return EntryState(anchor, "SECONDARY_UNKNOWN", True), None

    close = bar.get("close", bar.get("c"))
    end = bar.get("end")
    if not isinstance(close, (int, float)) or isinstance(close, bool) or close <= 0 or not end:
        return EntryState(anchor, "SECONDARY_UNKNOWN", True), None

    if close >= anchor.decision_price:
        return EntryState(anchor, "FIRST_BAR_CONTINUATION", True), None

    if reference_boundary_expired:
        return EntryState(anchor, "SECONDARY_EXPIRED_BOUNDARY", True), None
    if reference_bar is None or bool(reference_bar.get("missing", False)):
        return EntryState(anchor, "SECONDARY_UNKNOWN", True), None

    reference_open = reference_bar.get("open", reference_bar.get("o"))
    reference_start = reference_bar.get("start", end)
    if (
        not isinstance(reference_open, (int, float))
        or isinstance(reference_open, bool)
        or reference_open <= 0
        or not reference_start
    ):
        return EntryState(anchor, "SECONDARY_UNKNOWN", True), None

    event = {
        **_base(anchor),
        "eventType": "DIP_REPRICE_OPPORTUNITY",
        "sourceState": "FIRST_CLOSED_DIP",
        "opportunityTimestamp": str(reference_start),
        "observedFirstClose": float(close),
        "referenceStatus": "REFERENCE_OPEN",
        "referencePrice": float(reference_open),
        "quantityOwnedByEntry": False,
    }
    return EntryState(anchor, "DIP_REPRICE_EMITTED", True), event


def state_record(state: EntryState) -> dict[str, Any]:
    """Serializable audit state; contains no evaluator outcome fields."""
    return {
        "kernelVersion": KERNEL_VERSION,
        "contractStatus": CONTRACT_STATUS,
        "state": state.state,
        "secondaryTerminal": state.secondary_terminal,
        "anchor": asdict(state.anchor),
    }
