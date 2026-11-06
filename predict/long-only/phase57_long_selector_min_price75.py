"""Human-defined price eligibility overlay; parent score and ordering unchanged."""
import math
from numbers import Real

MIN_DECISION_PRICE_JPY = 75
POLICY_ID = 'LONG_ONLY_MIN_DECISION_PRICE_75_JPY_V1'

def price_status(decision_price):
    if isinstance(decision_price, bool) or not isinstance(decision_price, Real) or not math.isfinite(decision_price) or decision_price <= 0:
        return 'BLOCKED_INVALID_DECISION_PRICE'
    return 'INELIGIBLE_MIN_PRICE' if decision_price <= MIN_DECISION_PRICE_JPY else 'ELIGIBLE_MIN_PRICE'

def causal_status(row):
    status = price_status(row.get('decisionPrice'))
    if status == 'BLOCKED_INVALID_DECISION_PRICE': return status
    age = row.get('referenceAgeMin')
    if row.get('decisionPriceValid') != 1 or isinstance(age, bool) or not isinstance(age, Real) or not math.isfinite(age) or not 0 <= age <= 5:
        return 'BLOCKED_PARENT_PRICE_QUALITY'
    return status

def select_top5(rows):
    """One timestamp of already scored parent candidates; never reads labels."""
    eligible = [r for r in rows if causal_status(r) == 'ELIGIBLE_MIN_PRICE']
    if len({r['symbol'] for r in eligible}) != len(eligible): raise ValueError('DUPLICATE_SYMBOL')
    if any(isinstance(r.get('savedV1Score'), bool) or not isinstance(r.get('savedV1Score'), Real) or not math.isfinite(r['savedV1Score']) for r in eligible): raise ValueError('INVALID_PARENT_SCORE')
    return sorted(eligible, key=lambda r: (-r['savedV1Score'], str(r['symbol'])))[:5]
