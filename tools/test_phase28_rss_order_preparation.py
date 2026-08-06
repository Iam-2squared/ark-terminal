from tools.rss_order_preparation import (
    ORDER_TRIGGER_CELL,
    build_order_preparation,
    evaluate_phase28_activation_gate,
    normalize_rss_order_status,
    write_preparation_to_worksheet,
)


class FakeRange:
    def __init__(self, store, key):
        self.store = store
        self.key = key

    @property
    def Value(self):
        return self.store.get(self.key)

    @Value.setter
    def Value(self, value):
        self.store[self.key] = value


class FakeWorksheet:
    def __init__(self):
        self.store = {}

    def Range(self, key):
        return FakeRange(self.store, key)


def valid_input():
    return {
        "approval": {"status": "DRY_RUN_READY", "candidateHash": "abc"},
        "risk": {"status": "DRY_RUN_ALLOWED"},
        "killSwitch": {"status": "ARMED"},
        "candidate": {
            "symbol": "7203.T",
            "side": "BUY",
            "quantity": 100,
            "limitPrice": 2500,
        },
        "generatedAt": "2026-08-06T00:00:00+00:00",
    }


def test_preparation_keeps_order_trigger_false():
    result = build_order_preparation(valid_input())
    assert result.status == "PREPARED_FOR_LOCAL_REVIEW"
    assert result.cells[ORDER_TRIGGER_CELL] is False
    assert result.safety["brokerWriteAllowed"] is False
    assert result.safety["liveTradingAllowed"] is False


def test_blocked_preparation_cannot_write_excel():
    data = valid_input()
    data["approval"] = {"status": "PENDING"}
    result = build_order_preparation(data)
    assert result.status == "BLOCKED"
    try:
        write_preparation_to_worksheet(FakeWorksheet(), result)
    except ValueError:
        pass
    else:
        raise AssertionError("blocked preparation must not write")


def test_preview_write_never_enables_trigger():
    result = build_order_preparation(valid_input())
    sheet = FakeWorksheet()
    response = write_preparation_to_worksheet(sheet, result)
    assert sheet.store[ORDER_TRIGGER_CELL] is False
    assert response["liveOrders"] == 0
    assert response["brokerWrites"] == 0


def test_status_normalization_is_read_only():
    status = normalize_rss_order_status("入力エラー")
    assert status["status"] == "INPUT_ERROR"
    assert status["error"] is True
    assert status["readOnly"] is True


def test_activation_gate_never_auto_activates():
    gate = evaluate_phase28_activation_gate({
        "paperResolved": 500,
        "paperSessions": 100,
        "paperProfitFactor": 1.5,
        "paperMaxDrawdown": 0.05,
        "shadowSessions": 100,
        "criticalIncidents": 0,
        "killSwitchTestPassed": True,
        "guardianAndAccountRulesConfirmed": True,
    })
    assert gate["status"] == "READY_FOR_HUMAN_REVIEW"
    assert gate["automaticActivationAllowed"] is False
    assert gate["excelOrderTriggerAllowed"] is False
    assert gate["brokerWriteAllowed"] is False


def test_activation_gate_blocks_insufficient_evidence():
    gate = evaluate_phase28_activation_gate({})
    assert gate["status"] == "BLOCKED"
    assert "PAPER_SAMPLE_TOO_SMALL" in gate["blockers"]
    assert "KILL_SWITCH_TEST_REQUIRED" in gate["blockers"]
