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


def create_native_workbook():
    account = DummySheet(
        {
            "A1": "=RssCapacityList()",
            "A2": "現物買付可能額",
            "B2": "信用口座_保証金余裕額",
            "A3": "118,000",
            "B3": "－",
        }
    )

    positions = DummySheet(
        {
            "A1": '=RssPositionList(,,"A")',
            "A2": "銘柄コード",
            "B2": "銘柄名称",
            "C2": "口座区分",
            "D2": "保有数量",
            "E2": "発注数量",
            "F2": "平均取得価額",
            "G2": "時価",
            "H2": "前日比",
            "I2": "前日比率",
            "J2": "時価評価額",
            "K2": "評価損益額",
            "L2": "評価損益率",
            "M2": "銘柄情報等",
            "N2": "JAX時価",
            "O2": "JNX時価",
            "P2": "PER",
            "Q2": "PBR",
            "R2": "配当利回り",
            "A3": "4755",
            "B3": "楽天グループ",
            "C3": "特定",
            "D3": 100,
            "E3": 0,
            "F3": 800,
            "G3": 840,
            "J3": 84000,
            "K3": 4000,
            "L3": 5,
            "A4": "9432",
            "B4": "NTT",
            "C4": "特定",
            "D4": 1000,
            "E4": 100,
            "F4": 150,
            "G4": 151,
            "J4": 151000,
            "K4": 1000,
            "L4": 0.6667,
            "A5": None,
        }
    )

    return DummyWorkbook(
        {
            "ArkAccount": account,
            "ArkPositions": positions,
        }
    )


def create_legacy_workbook():
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
            "A3": None,
        }
    )

    return DummyWorkbook(
        {
            "ArkAccount": account,
            "ArkPositions": positions,
        }
    )


def test_native_rss_snapshot_is_normalized_and_private():
    snapshot = rss_account_bridge.read_broker_snapshot(
        create_native_workbook(),
        now="2026-08-05T12:30:00+00:00",
    )

    assert snapshot["readOnly"] is True
    assert snapshot["sourceMode"] == "marketspeed-native-rss"
    assert snapshot["connection"]["connected"] is True
    assert snapshot["connection"]["authenticated"] is True
    assert snapshot["connection"]["accountId"] is None
    assert snapshot["account"]["accountId"] is None
    assert snapshot["account"]["cash"] is None
    assert snapshot["account"]["buyingPower"] == 118000
    assert snapshot["account"]["marketValue"] == 235000
    assert snapshot["account"]["equity"] is None
    assert snapshot["account"]["unrealizedPnl"] == 5000
    assert snapshot["account"]["availableMetrics"]["cash"] is False
    assert snapshot["account"]["availableMetrics"]["buyingPower"] is True
    assert snapshot["orders"] == []


def test_native_positions_are_read_from_rss_list_rows():
    positions = rss_account_bridge.read_positions(
        create_native_workbook(),
        now="2026-08-05T12:30:00+00:00",
    )

    assert len(positions) == 2
    assert positions[0]["symbol"] == "4755.T"
    assert positions[0]["quantity"] == 100
    assert positions[0]["unrealizedPnl"] == 4000
    assert positions[1]["symbol"] == "9432.T"
    assert positions[1]["marketValue"] == 151000
    assert positions[1]["orderQuantity"] == 100
    assert positions[1]["availableQuantity"] == 1000
    assert all(position["readOnly"] is True for position in positions)
    assert all(
        position["sourceMode"] == "marketspeed-native-rss"
        for position in positions
    )


def test_legacy_normalized_sheet_remains_supported():
    snapshot = rss_account_bridge.read_broker_snapshot(
        create_legacy_workbook(),
        now="2026-08-05T12:30:00+00:00",
    )

    assert snapshot["sourceMode"] == "legacy-normalized-sheet"
    assert snapshot["account"]["cash"] == 120000
    assert snapshot["account"]["equity"] == 350000
    assert len(snapshot["positions"]) == 1


def test_description_text_does_not_fake_a_connected_account():
    workbook = DummyWorkbook(
        {
            "ArkAccount": DummySheet(
                {
                    "B2": "実際の現金残高",
                    "B3": "実際の買付可能額",
                    "B4": "保有株の時価総額",
                    "B5": "総資産",
                }
            ),
            "ArkPositions": DummySheet({"A2": None}),
        }
    )

    with pytest.raises(RuntimeError, match="有効な数値"):
        rss_account_bridge.read_broker_snapshot(workbook)


def test_missing_account_sheet_fails_closed():
    workbook = DummyWorkbook(
        {
            "ArkPositions": DummySheet({"A2": None}),
        }
    )

    with pytest.raises(RuntimeError, match="ArkAccount"):
        rss_account_bridge.read_broker_snapshot(workbook)


def test_broker_endpoints_return_read_only_native_snapshot(monkeypatch):
    snapshot = rss_account_bridge.read_broker_snapshot(
        create_native_workbook(),
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
    assert account.json()["account"]["buyingPower"] == 118000
    assert account.json()["account"]["equity"] is None
    assert account.json()["account"]["accountId"] is None

    positions = client.get("/broker/positions")
    assert positions.status_code == 200
    assert positions.json()["count"] == 2

    snapshot_response = client.get("/broker/snapshot")
    assert snapshot_response.status_code == 200
    assert snapshot_response.json()["orders"] == []

    assert client.post("/broker/account").status_code in {404, 405}
    assert client.delete("/broker/positions").status_code in {404, 405}


def test_connection_reports_configuration_error_without_fake_values(monkeypatch):
    def fail():
        raise RuntimeError(
            "ArkAccountのRssCapacityList出力に現物買付可能額がありません。"
        )

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
    assert "RssCapacityList" in body["message"]


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

    assert allowed.status_code in {200, 204}
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

    assert denied.status_code == 400
    assert "access-control-allow-private-network" not in denied.headers
