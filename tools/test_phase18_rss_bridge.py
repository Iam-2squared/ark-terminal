from __future__ import annotations

from fastapi.testclient import TestClient

from tools import rss_bridge


class DummySheet:
    def __init__(self, values):
        self.values = values

    class _Range:
        def __init__(self, value):
            self.Value = value

    def Range(self, cell):
        return self._Range(self.values.get(cell))


def install_sheet(monkeypatch):
    sheet = DummySheet({
        'A1': 840.0, 'B1': 820.0, 'C1': 850.0, 'D1': 810.0,
        'E1': 1200000, 'F1': 839.0, 'G1': 840.0, 'H1': 800.0, 'I1': 830.0,
        'A2': 151.0, 'H2': 150.0,
        'A3': 2914.5, 'H3': 2900.0,
        'A4': 5958.0, 'H4': 6000.0,
    })
    monkeypatch.setattr(rss_bridge, 'read_sheet_snapshot', lambda: (object(), sheet))
    monkeypatch.setattr(rss_bridge, 'release_com', lambda: None)


def test_health_is_read_only():
    client = TestClient(rss_bridge.app)
    data = client.get('/health').json()
    assert data['mode'] == 'read_only'
    assert data['order_creation'] is False
    assert data['order_transmission'] is False
    assert data['parts'] == list(range(1, 11))


def test_price_and_batch(monkeypatch):
    install_sheet(monkeypatch)
    client = TestClient(rss_bridge.app)
    assert client.get('/price/4755.T').json()['price'] == 840.0
    batch = client.get('/prices', params={'symbols': '4755.T,7203.T'}).json()
    assert batch['count'] == 2
    assert batch['order_transmission'] is False


def test_prediction_portfolio_and_watchlist(monkeypatch):
    install_sheet(monkeypatch)
    client = TestClient(rss_bridge.app)
    assert client.get('/prediction/4755.T').json()['prediction_ready'] is True
    assert client.get('/portfolio/realtime', params={'symbols': '4755.T,9432.T'}).json()['count'] == 2
    assert client.post('/watchlist/4755.T', params={'target_price': 800}).status_code == 200
    assert client.get('/watchlist/check').json()['count'] == 1
    assert client.delete('/watchlist/4755.T').json()['removed'] is True


def test_parts6_to_8_monitor_orderbook_and_market(monkeypatch):
    install_sheet(monkeypatch)
    client = TestClient(rss_bridge.app)

    monitor = client.get('/monitor/realtime').json()
    assert monitor['count'] == 4
    assert monitor['alerts'][0]['symbol'] == '4755.T'

    book = client.get('/orderbook/4755.T').json()
    assert book['best_bid'] == 839.0
    assert book['best_ask'] == 840.0
    assert book['available'] is True
    assert book['order_creation'] is False

    market = client.get('/market/4755.T').json()
    assert market['volume'] == 1200000.0
    assert market['vwap'] == 830.0
    assert market['change_percent'] == 5.0


def test_parts9_and_10_ai_and_completion(monkeypatch):
    install_sheet(monkeypatch)
    client = TestClient(rss_bridge.app)

    ai = client.get('/ai/realtime/4755.T').json()
    assert ai['stance'] == 'positive'
    assert ai['decision_support_only'] is True
    assert ai['automatic_order'] is False
    assert ai['order_transmission'] is False

    status = client.get('/phase18/status').json()
    assert status['completion_percent'] == 100
    assert status['completed_parts'] == list(range(1, 11))
    assert status['order_creation'] is False
