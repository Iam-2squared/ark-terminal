from __future__ import annotations

from phase58_excel_5m_history_pack_windowed import (
    RSSCHART_MAX_DISPLAY_COUNT,
    RSSCHART_READ_RANGE,
    _read_rsschart_display_window,
)


class _FakeRange:
    def __init__(self, value):
        self.Value = value


class _FakeSheet:
    def __init__(self, value):
        self.value = value
        self.requested = []

    def Range(self, address):
        self.requested.append(address)
        return _FakeRange(self.value)


def test_reads_full_3000_row_rsschart_window_instead_of_used_range():
    marker = (("ok",),)
    sheet = _FakeSheet(marker)
    out = _read_rsschart_display_window(sheet)
    assert out == marker
    assert RSSCHART_MAX_DISPLAY_COUNT == 3000
    assert RSSCHART_READ_RANGE == "A1:J3002"
    assert sheet.requested == ["A1:J3002"]
