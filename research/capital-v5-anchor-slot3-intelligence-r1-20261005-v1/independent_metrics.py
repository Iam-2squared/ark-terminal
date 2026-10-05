"""Independent post-main exact economic/quality/protection evaluator.

No Primary replay, adapter, policy or evaluator is imported. All comparisons use
Fraction(Decimal source cells), including mean, median, rates and drawdowns.
Teachers and saved Slot1/2 membership enter only here, after funded decisions.
"""

from decimal import Decimal
from fractions import Fraction as F


def exact(value):
    if isinstance(value, F):
        return value
    if isinstance(value, dict) and 'numerator' in value:
        return F(value['numerator'], value['denominator'])
    return F(Decimal(str(value)))


def pack(value):
    value = exact(value)
    return {'numerator': value.numerator, 'denominator': value.denominator}


def drawdown(points, opening):
    peak, maximum = exact(opening), F(0)
    for point in points:
        equity = exact(point['equity'])
        assert equity > 0
        peak = max(peak, equity)
        maximum = max(maximum, (peak - equity) / peak)
    return maximum


def capital(daily, curves):
    if (len(daily) != 38 or any(d['status'] != 'COMPLETE' or not d['primary_chain'] or
            d['ending_cash'] is None or d['blockers'] or d['open_obligations'] for d in daily)):
        return {'status': 'NOT_EVALUATED'}
    sessions = [d['session'] for d in daily]
    assert len(sessions) == len(set(sessions)) == 38 and sessions == sorted(sessions)
    for prior, following in zip(daily, daily[1:]):
        assert exact(prior['ending_cash']) == exact(following['starting_cash'])
    by_session = {day: [] for day in sessions}
    for point in curves:
        assert point['primary_chain'] and point['session'] in by_session
        by_session[point['session']].append(point)
    assert all(len(by_session[day]) == 392 for day in sessions)
    windows = []
    for start in range(19):
        days = daily[start:start + 20]
        before, end = exact(days[0]['starting_cash']), exact(days[-1]['ending_cash'])
        points = [point for day in sessions[start:start + 20] for point in by_session[day]]
        growth = end / before
        windows.append({'start_session': days[0]['session'], 'end_session': days[-1]['session'],
                        'growth': pack(growth), 'amount_from_1m': pack(1000000 * growth),
                        'maxdd': pack(drawdown(points, before)), 'point_N': len(points),
                        'hit_2x': growth >= 2, 'below_1m': growth < 1})
    growths = sorted(exact(w['growth']) for w in windows)
    daily_returns = [exact(d['ending_cash']) / exact(d['starting_cash']) - 1 for d in daily]
    return {'status': 'EVALUATED', 'session_ids': sessions, 'windows': windows,
            'statistics': {'minimum': pack(growths[0]), 'mean': pack(sum(growths, F(0)) / 19),
                           'median': pack(growths[9]), 'maximum': pack(growths[-1]),
                           'hit_2x_N': sum(w['hit_2x'] for w in windows),
                           'below_1m_window_N': sum(w['below_1m'] for w in windows)},
            'full_maxdd': pack(drawdown(curves, daily[0]['starting_cash'])),
            'negative_session_N': sum(r < 0 for r in daily_returns),
            'worst_daily_return': pack(min(daily_returns)),
            'final38_equity_secondary_only': pack(daily[-1]['ending_cash'])}


def quality(decisions, trades, teachers, v5_decisions, v5_trades):
    teacher = {r['entry_id']: r for r in teachers}
    funded = [r for r in decisions if r['quantity'] >= 100]
    ids = [r['entry_id'] for r in funded]
    assert len(ids) == len(set(ids))
    trade = {r['entry_id']: r for r in trades}
    baseline_trade = {r['entry_id']: r for r in v5_trades}
    assert len(trade) == len(trades) and set(trade) == set(ids)
    counts = dict.fromkeys(('U5', 'U10', 'Medium', 'Weak', 'below3', 'loser_le_zero',
                           'positive', 'strict_negative', 'exact_zero'), 0)
    gross_loss = F(0)
    for entry_id in ids:
        potential = exact(teacher[entry_id]['potential_return'])
        pnl = exact(trade[entry_id]['pnl'])
        counts['U5'] += potential >= F(5, 100)
        counts['U10'] += potential >= F(10, 100)
        counts['Medium'] += F(3, 100) <= potential < F(5, 100)
        counts['Weak'] += potential < F(2, 100)
        counts['below3'] += potential < F(3, 100)
        counts['loser_le_zero'] += pnl <= 0
        counts['positive'] += pnl > 0
        counts['strict_negative'] += pnl < 0
        counts['exact_zero'] += pnl == 0
        if pnl < 0:
            gross_loss -= pnl
    protected = {}
    for slot in (1, 2):
        group = [r['entry_id'] for r in v5_decisions if r['quantity'] >= 100 and r['funded_slot'] == slot]
        assert len(group) == len(set(group)) == (41 if slot == 1 else 59)
        candidate_pnl = sum((exact(trade[i]['pnl']) for i in group if i in trade), F(0))
        native_pnl = sum((exact(baseline_trade[i]['pnl']) for i in group), F(0))
        missing = sorted(set(group) - set(ids))
        protected[str(slot)] = {'group_N': len(group), 'funded_N': len(group) - len(missing),
                                'missing_ids': missing, 'candidate_group_pnl': pack(candidate_pnl),
                                'V5_group_pnl': pack(native_pnl),
                                'PASS': not missing and candidate_pnl >= native_pnl}
    return {'denominator': len(ids), 'count': counts,
            'rate': {name: pack(F(value, len(ids))) for name, value in counts.items()},
            'gross_loss': pack(gross_loss), 'protectedSlot12': protected,
            'protected_PASS': all(p['PASS'] for p in protected.values())}


def evaluate(output, v5_output, teachers, independent_mismatch=0, causal_canaries_pass=True):
    result = capital(output['daily'], output['curves'])
    if result['status'] != 'EVALUATED':
        return {'status': 'NOT_EVALUATED', 'capital': result, 'quality': None,
                'gates': {f'E{i}': 'NOT_EVALUATED' for i in range(8)} |
                         {f'Q{i}': 'NOT_EVALUATED' for i in range(1, 12)}, 'eligible': False}
    baseline = capital(v5_output['daily'], v5_output['curves'])
    assert baseline['status'] == 'EVALUATED'
    q = quality(output['decisions'], output['trades'], teachers,
                v5_output['decisions'], v5_output['trades'])
    bq = quality(v5_output['decisions'], v5_output['trades'], teachers,
                 v5_output['decisions'], v5_output['trades'])
    paired = list(zip(result['windows'], baseline['windows']))
    ids_equal = [(a['start_session'], a['end_session']) for a, b in paired] == [
                 (b['start_session'], b['end_session']) for a, b in paired]
    diffs = [exact(a['growth']) - exact(b['growth']) for a, b in paired]
    stats, bstats = result['statistics'], baseline['statistics']
    counts, n = q['count'], q['denominator']
    gates = {
        'E0': result['session_ids'] == baseline['session_ids'] and len(paired) == 19 and ids_equal,
        'E1': all(d >= 0 for d in diffs),
        'E2': exact(stats['median']) > exact(bstats['median']),
        'E3': exact(stats['mean']) > exact(bstats['mean']),
        'E4': exact(stats['minimum']) >= exact(bstats['minimum']),
        'E5': exact(stats['maximum']) >= exact(bstats['maximum']),
        'E6': stats['hit_2x_N'] >= bstats['hit_2x_N'] and stats['below_1m_window_N'] == 0,
        'E7': all(exact(a['maxdd']) <= exact(b['maxdd']) for a, b in paired) and
              exact(result['full_maxdd']) <= exact(baseline['full_maxdd']),
        'Q1': counts['U5'] >= 50,
        'Q2': counts['U10'] >= 26,
        'Q3': counts['Medium'] >= 27,
        'Q4': counts['Weak'] <= 58 and F(counts['Weak'], n) <= F(58, 150),
        'Q5': counts['below3'] <= 73 and F(counts['below3'], n) <= F(73, 150),
        'Q6': counts['loser_le_zero'] < 82 and F(counts['loser_le_zero'], n) < F(82, 150),
        'Q7': counts['positive'] >= 68,
        'Q8': exact(q['gross_loss']) <= exact(bq['gross_loss']),
        'Q9': result['negative_session_N'] <= baseline['negative_session_N'] and
              exact(result['worst_daily_return']) >= exact(baseline['worst_daily_return']),
        'Q10': q['protected_PASS'],
        'Q11': independent_mismatch == 0 and causal_canaries_pass,
    }
    return {'status': 'EVALUATED', 'capital': result, 'quality': q, 'gates': gates,
            'eligible': all(gates.values()),
            'paired19': {'better': sum(d > 0 for d in diffs), 'equal': sum(d == 0 for d in diffs),
                         'worse': sum(d < 0 for d in diffs), 'worst_paired_delta': pack(min(diffs))}}
