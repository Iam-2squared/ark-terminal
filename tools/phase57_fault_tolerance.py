"""G8 fail-closed runtime fault state machine.

The state machine has no transmission capability. Any critical fault latches the
kill switch. Recovery requires an explicit reset plus a clean health check.
"""
from __future__ import annotations

from dataclasses import dataclass, field

SAFETY = {
    "executionAllowed": False,
    "brokerWriteAllowed": False,
    "excelOrderWriteAllowed": False,
    "rssOrderFunctionAllowed": False,
    "liveTradingAllowed": False,
    "paperTradingAllowed": False,
    "automaticPromotionAllowed": False,
    "productionUpdateAllowed": False,
    "transmitted": False,
}

CRITICAL_FAULTS = {
    "RSS_DISCONNECTED",
    "ACCOUNT_SNAPSHOT_STALE",
    "RECONCILIATION_MISMATCH",
    "UNKNOWN_ORDER",
    "PARTIAL_FILL",
    "RESTART_STATE_UNVERIFIED",
    "DUPLICATE_OR_REPLAY",
    "FINALIZED_BAR_REVISED",
}

RETRYABLE_FAULTS = {"EXCEL_COM_BUSY"}


@dataclass
class RuntimeSafetyState:
    max_com_retries: int = 3
    kill_switch_latched: bool = False
    faults: list[str] = field(default_factory=list)
    com_retry_count: int = 0

    def observe_fault(self, fault: str) -> dict:
        code = str(fault).strip().upper()
        if code in RETRYABLE_FAULTS:
            self.com_retry_count += 1
            if self.com_retry_count > self.max_com_retries:
                self._latch("EXCEL_COM_RETRY_EXHAUSTED")
        elif code in CRITICAL_FAULTS:
            self._latch(code)
        else:
            self._latch(f"UNKNOWN_FAULT:{code or 'EMPTY'}")
        return self.snapshot()

    def observe_healthy_com_read(self) -> dict:
        self.com_retry_count = 0
        return self.snapshot()

    def explicit_reset(self, *, health_check_passed: bool) -> dict:
        if not health_check_passed:
            self._latch("RESET_HEALTH_CHECK_FAILED")
            return self.snapshot()
        self.kill_switch_latched = False
        self.faults.clear()
        self.com_retry_count = 0
        return self.snapshot()

    def _latch(self, code: str) -> None:
        self.kill_switch_latched = True
        if code not in self.faults:
            self.faults.append(code)

    def snapshot(self) -> dict:
        return {
            "schemaId": "ARK_RUNTIME_SAFETY_STATE_V1",
            "killSwitchLatched": self.kill_switch_latched,
            "newIntentAllowed": False,
            "executionAllowed": False,
            "transmitted": False,
            "comRetryCount": self.com_retry_count,
            "maxComRetries": self.max_com_retries,
            "faults": list(self.faults),
            "safety": dict(SAFETY),
        }


def bounded_com_read(read_fn, state: RuntimeSafetyState):
    """Retry only RPC_E_CALL_REJECTED-like busy errors; otherwise fail closed."""
    attempts = 0
    while True:
        try:
            value = read_fn()
            state.observe_healthy_com_read()
            return value
        except Exception as exc:
            text = str(exc).upper()
            retryable = "RPC_E_CALL_REJECTED" in text or "0X80010001" in text
            if not retryable:
                state.observe_fault("UNKNOWN_FAULT:COM_READ_FAILURE")
                raise
            attempts += 1
            state.observe_fault("EXCEL_COM_BUSY")
            if state.kill_switch_latched or attempts > state.max_com_retries:
                raise RuntimeError("EXCEL_COM_RETRY_EXHAUSTED") from exc
