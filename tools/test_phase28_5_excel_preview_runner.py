from __future__ import annotations

from types import SimpleNamespace

import tools.run_phase28_excel_preview as runner


class FakeRange:
    def __init__(self, store: dict[str, object], cell: str):
        self.store = store
        self.cell = cell

    @property
    def Value(self):
        return self.store.get(self.cell)

    @Value.setter
    def Value(self, value):
        self.store[self.cell] = value


class FakeWorksheet:
    def __init__(self):
        self.store: dict[str, object] = {}

    def Range(self, cell: str):
        return FakeRange(self.store, cell)


class FakeWorksheets:
    def __init__(self, worksheet: FakeWorksheet):
        self.worksheet = worksheet

    def __call__(self, name: str):
        if name != "ARK_ORDER":
            raise KeyError(name)
        return self.worksheet


class FakeWorkbook:
    def __init__(self, worksheet: FakeWorksheet):
        self.Worksheets = FakeWorksheets(worksheet)


def test_runner_writes_preview_and_keeps_trigger_false():
    worksheet = FakeWorksheet()
    workbook = FakeWorkbook(worksheet)

    result = runner.run_excel_preview(
        "7203.T",
        100,
        1.0,
        workbook_reader=lambda: (SimpleNamespace(), workbook),
        com_releaser=lambda: None,
    )

    assert result["status"] == "PREVIEW_WRITTEN"
    assert worksheet.store["B2"] == "7203.T"
    assert worksheet.store["B4"] == 100
    assert worksheet.store["B6"] == 1.0
    assert worksheet.store["B9"] is False
    assert result["brokerWrites"] == 0
    assert result["liveOrders"] == 0
    assert result["safety"]["brokerWriteAllowed"] is False
    assert result["safety"]["liveTradingAllowed"] is False


def test_runner_reports_missing_order_sheet():
    class MissingWorkbook:
        class Worksheets:
            def __new__(cls, name: str):
                raise KeyError(name)

    try:
        runner.run_excel_preview(
            "7203.T",
            100,
            1.0,
            workbook_reader=lambda: (SimpleNamespace(), MissingWorkbook()),
            com_releaser=lambda: None,
        )
    except RuntimeError as exc:
        assert "ARK_ORDER" in str(exc)
    else:
        raise AssertionError("missing ARK_ORDER sheet must fail")


def test_validation_payload_is_dry_run_only():
    payload = runner.build_validation_payload("7203.T", 100, 1.0)
    assert payload["approval"]["status"] == "DRY_RUN_READY"
    assert payload["risk"]["status"] == "DRY_RUN_ALLOWED"
    assert payload["killSwitch"]["status"] == "ARMED"
    assert payload["candidate"]["side"] == "BUY"
