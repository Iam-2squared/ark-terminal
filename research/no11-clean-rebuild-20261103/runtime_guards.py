"""New, source-only runtime guards. No order I/O, model changes or cash adoption.

These helpers are called by the separately generated coordinator. They never
turn an observer result into a new ARK fill and never clear external exclusions.
"""
from __future__ import annotations


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError('NO11_CLEAN_' + reason)


def validate_fee_course(config: dict) -> None:
    """Optional explicit fee profile, keeping old non-profile configs compatible.

ZERO is an internal configuration value, not a claim that broker settings were
read or changed. Existing transport permission and cash gates remain untouched.
"""
    course = config.get('feeCourse')
    if course is None:
        return
    require(type(course) is str and course in ('ZERO', 'OTHER'), 'FEE_COURSE_UNKNOWN')
    require(course != 'ZERO' or config.get('orderTerms', {}).get('sor') is True,
            'ZERO_REQUIRES_SOR')


def recheck_exit(service, command: dict, at: str) -> str:
    """Recheck only a prepared SELL, before IN_FLIGHT and any transport call.

Re-reading a local observer is not an atomic broker lock. A manual operation
not yet observed cannot be detected here; already-sent orders are not cancelled.
"""
    if command.get('kind') != 'ORDER' or command.get('side') != 'SELL':
        return at
    if service.config.get('evidenceMode') == 'BROKER_OBSERVATION':
        require(service.observe_file(at) is True, 'EXIT_OBSERVATION_FAILED')
        newer = service.clock()
        # The coordinator's source and ledger validators enforce JST syntax.
        from no11_broker_execution_ledger import instant
        require(instant(newer, service.session) >= instant(at, service.session),
                'EXIT_CLOCK_REVERSED')
        at = newer
    require(service._source_current(at), 'EXIT_CURRENT_SOURCE_REQUIRED')
    state = service.book.snapshot(at)
    order = state.get('orders', {}).get(command.get('intentId'))
    require(type(order) is dict and order.get('commandId') == command.get('commandId')
            and all(order.get(k) == command.get(k)
                    for k in ('symbol', 'side', 'quantity', 'account')),
            'EXIT_RECORDED_ORDER_REQUIRED')
    quantity = order.get('quantity')
    position = state.get('positions', {}).get(order.get('entryId'))
    require(type(position) is dict and type(quantity) is int and quantity > 0
            and type(position.get('quantity')) is int
            and quantity <= position['quantity']
            and position.get('symbol') == order.get('symbol')
            and position.get('account') == order.get('account'),
            'EXIT_REMAINING_OWNERSHIP_REQUIRED')
    # Existing sticky external-symbol exclusion, same-account holding identity,
    # and manual pending-SELL reservation checks remain the authority.
    service._sell_safe(order, at)
    # A mismatch in total holding, even an excess, is not adopted as ARK stock.
    # Same-symbol mixed manual ownership is conservatively held for review.
    from no11_broker_fill_attribution import symbol
    holdings = [p for p in service.source['positions']
                if symbol(p['symbol']) == order['symbol']
                and p['account'] == order['account']]
    owned = [p for p in state['positions'].values()
             if p.get('symbol') == order['symbol'] and p.get('account') == order['account']]
    require(all(type(p.get('quantity')) is int and p['quantity'] >= 0 for p in owned),
            'EXIT_OWNED_QUANTITY_INVALID')
    total = sum(p['quantity'] for p in owned)
    require(len(holdings) == 1 and holdings[0]['quantity'] == total,
            'EXIT_MIXED_OR_CHANGED_HOLDING')
    return at
