"""Authorized valuation, not imputation: latest observed Close within [t-5,t)."""
from decimal import Decimal

CONTRACT_ID = 'CAPITAL_OBSERVED_CLOSED_5M_WINDOW_MTM_REFERENCE_V1'

def latest_window_bar(bars, grid_minute):
    eligible = {}
    for bar in bars:
        minute = int(bar[0])
        if not grid_minute - 5 <= minute < grid_minute:
            continue
        close = Decimal(str(bar[4]))
        if not close.is_finite() or close <= 0:
            continue
        if minute in eligible and eligible[minute] != bar:
            raise ValueError('CONFLICTING_SAVED_WINDOW_SOURCE')
        eligible[minute] = bar
    if not eligible:
        return None
    return eligible[max(eligible)]

