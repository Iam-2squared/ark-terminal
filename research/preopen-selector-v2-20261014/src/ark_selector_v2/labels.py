"""Labels live separately from forecasting inputs. OHLC cannot establish order."""
from dataclasses import dataclass
from fractions import Fraction as F
from .contracts import Candle, LABEL_ID


@dataclass(frozen=True)
class Label:
    status: str
    b: int | None
    r: int | None
    up_pct: F | None
    adverse_pct: F | None
    close_pct: F | None
    exact_zero: bool | None
    raw_winner: tuple[bool, ...] | None
    clean_winner: tuple[bool, ...] | None
    raw_loser: tuple[bool, ...] | None
    utility: int | None
    label_id: str = LABEL_ID


def label(row: Candle) -> Label:
    row.validate()
    if row.open is None:
        return Label(row.status, None, None, None, None, None, None, None, None, None, None)
    o, h, l, c = row.open, row.high, row.low, row.close
    assert h is not None and l is not None and c is not None
    up = 100 * (h/o-1)
    adverse = 100 * (1-l/o)
    raw = tuple(100*h >= (100+k)*o for k in range(1, 6))
    losers = tuple(100*l <= (100-k)*o for k in (1, 2, 3, 5))
    r = 2 if 100*l <= 95*o else 1 if 100*l <= 97*o else 0
    b = sum(raw)
    clean = tuple(v and r == 0 for v in raw)
    return Label("KNOWN", b, r, up, adverse, 100*(c/o-1), h == o,
                 raw, clean, losers, sum(clean))
