from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from tools import rss_account_bridge, rss_bridge


class DummySheet:
    def __init__(self, values):
        self.values = values

    class _Range:
        def __init__(self, value):
            self.Value = value

    def Range(self, address):
        return self._Range(self.values.get(address))


class DummyWorkbook:
    def __init__(self, sheets):
        self.sheets = sheets

    def Worksheets(self, name):
        if name not in self.sheets:
            raise KeyError(name)
        return self.sheets[name]


def create_workbook():
    account = DummySheet(
        {
            "B2": "120,000",
            "B3": 118000,
            "B4": 230000,
            "B5": 350000,
            "B6": 1200,
            "B7": -4500,
            "B8": "JPY",
            "B9": datetime(2026, 8, 5, 12, 30, tzinfo=timezone.utc),
            "B10": "未成年口座",
        }
    )

    positions = DummySheet(
        {
            "A2": "4755",
            "B2": "楽天グループ",
            "C2": 100,
            "D2": 100,
            "E2": 800,
            "F2": 840,
            "G2": 84000,
            "H2": 4000,
            "I2": 5,
            "J2": "JPY",
            "K2": "特定",
            "L2": "2026-08-05T12:30:00+00:00",
            "A3": "9432.T",
            "B3": "NTT",
            "C3": 1000,
            "D3": 1000,
            "E3": 150,
            "F3": 151,
            "G3": None,
            "H3": None,
            "I3": None,
            "J3": "JPY",
            "K3": "特定",
            "L3": None,
            "A4": None,
        }
    )

    return DummyWorkbook(
        {
            "ArkAccount": account,
            "ArkPositions": positions,
        }
    )


def test_account_snapshot_is_normalized_and_private():
    snapshot = rss_account_bridge.read_broker_snapshot(
        create_workbook(),
        now="2026-08-05T12:30:00+00:00",
    )

    assert snapshot["readOnly"] is True
    assert snapshot["connection"]["connected"] is True
    assert snapshot["connection"]["authenticated"] is True
    assert snapshot["connection"]["accountId"] is None
    assert snapshot["account"]["accountId"] is None
    assert snapshot["account"]["cash"] == 120000
    assert snapshot["account"]["marketValue"] == 230000
    assert snapshot["account"]["equity"] == 350000
    assert snapshot["account"]["unrealizedPnl"] == -4500
    assert snapshot["orders"] == []


def test_positions_are_read_from_excel_rows():
    positions = rss_account_bridge.read_positions(
        create_workbook(),
        now="2026-08-05T12:30:00+00:00",
    )

    assert len(positions) == 2
    assert positions[0]["symbol"] == "4755.T"
    assert positions[0]["quantity"] == 100
    assert positions[0]["unrealizedPnl"] == 4000
    assert positions[1]["symbol"] == "9432.T"
    assert positions[1]["marketValue"] == 151000
    assert positions[1]["unrealizedPnl"] == 1000
    assert all(position["readOnly"] is True for position in positions)


def test_missing_account_sheet_fails_closed():
    workbook = DummyWorkbook(
        {
            "ArkPositions": DummySheet({"A2": None}),
        }
    )

    with pytest.raises(RuntimeError, match="ArkAccount"):
        rss_account_bridge.read_broker_snapshot(workbook)


def test_broker_endpoints_return_read_only_snapshot(monkeypatch):
    snapshot = rss_account_bridge.read_broker_snapshot(
        create_workbook(),
        now="2026-08-05T12:30:00+00:00",
    )

    monkeypatch.setattr(
        rss_bridge,
        "read_account_snapshot_from_excel",
        lambda: snapshot,
    )

    client = TestClient(rss_bridge.app)

    connection = client.get("/broker/connection")
    assert connection.status_code == 200
    assert connection.json()["connected"] is True
    assert connection.json()["readOnly"] is True

    account = client.get("/broker/account")
    assert account.status_code == 200
    assert account.json()["account"]["equity"] == 350000
    assert account.json()["account"]["accountId"] is None

    positions = client.get("/broker/positions")
    assert positions.status_code == 200
    assert positions.json()["count"] == 2

    snapshot_response = client.get("/broker/snapshot")
    assert snapshot_response.status_code == 200
    assert snapshot_response.json()["orders"] == []

    assert client.post("/broker/account").status_code == 405
    assert client.delete("/broker/positions").status_code == 405


def test_connection_reports_configuration_error_without_fake_values(monkeypatch):
    def fail():
        raise RuntimeError("ArkAccountシートに口座データがありません。")

    monkeypatch.setattr(
        rss_bridge,
        "read_account_snapshot_from_excel",
        fail,
    )

    client = TestClient(rss_bridge.app)
    response = client.get("/broker/connection")

    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is False
    assert body["authenticated"] is False
    assert body["accountId"] is None
    assert body["lastSyncAt"] is None
    assert "ArkAccount" in body["message"]


def test_cors_is_restricted_to_known_origins():
    assert "https://ark-terminal.vercel.app" in rss_bridge.ALLOWED_ORIGINS
    assert "*" not in rss_bridge.ALLOWED_ORIGINS


def test_private_network_preflight_is_allowed_only_for_known_origin():
    client = TestClient(rss_bridge.app)

    allowed = client.options(
        "/broker/connection",
        headers={
            "Origin": "https://ark-terminal.vercel.app",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-ark-read-only",
            "Access-Control-Request-Private-Network": "true",
        },
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == (
        "https://ark-terminal.vercel.app"
    )
    assert allowed.headers["access-control-allow-private-network"] == "true"

    denied = client.options(
        "/broker/connection",
        headers={
            "Origin": "https://example.invalid",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-ark-read-only",
            "Access-Control-Request-Private-Network": "true",
        },
    )

    assert "access-control-allow-private-network" not in denied.headers
