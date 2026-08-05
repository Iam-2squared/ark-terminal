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


def test_health_is_read_only():
    client = TestClient(rss_bridge.app)
    response = client.get('/health')
    assert response.status_code == 200
    data = response.json()
    assert data['mode'] == 'read_only'
    assert data['order_creation'] is False
    assert data['order_transmission'] is False
    assert data['order_cancellation'] is False
    assert data['phase'] == 19
    assert data['parts'] == [1, 2, 3, 4, 5, 6]
    assert data['market_data_phase'] == 18
    assert data['account_bridge'] is True


def test_price_and_batch(monkeypatch):
    sheet = DummySheet({'A1': 840.0, 'A2': 151.0, 'A3': 2914.5, 'A4': 5958.0})
    monkeypatch.setattr(rss_bridge, 'read_sheet_snapshot', lambda: (object(), sheet))
    monkeypatch.setattr(rss_bridge, 'release_com', lambda: None)

    client = TestClient(rss_bridge.app)
    single = client.get('/price/4755.T')
    assert single.status_code == 200
    assert single.json()['price'] == 840.0

    batch = client.get('/prices', params={'symbols': '4755.T,7203.T'})
    assert batch.status_code == 200
    assert batch.json()['count'] == 2
    assert batch.json()['order_transmission'] is False


def test_prediction_portfolio_and_watchlist(monkeypatch):
    sheet = DummySheet({'A1': 840.0, 'A2': 151.0, 'A3': 2914.5, 'A4': 5958.0})
    monkeypatch.setattr(rss_bridge, 'read_sheet_snapshot', lambda: (object(), sheet))
    monkeypatch.setattr(rss_bridge, 'release_com', lambda: None)

    client = TestClient(rss_bridge.app)

    prediction = client.get('/prediction/4755.T')
    assert prediction.status_code == 200
    assert prediction.json()['prediction_ready'] is True

    portfolio = client.get('/portfolio/realtime', params={'symbols': '4755.T,9432.T'})
    assert portfolio.status_code == 200
    assert portfolio.json()['count'] == 2

    add = client.post('/watchlist/4755.T', params={'target_price': 800})
    assert add.status_code == 200
    check = client.get('/watchlist/check')
    assert check.status_code == 200
    assert check.json()['count'] == 1

    remove = client.delete('/watchlist/4755.T')
    assert remove.status_code == 200
    assert remove.json()['removed'] is True
