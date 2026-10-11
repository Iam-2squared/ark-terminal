"""SYNTHETIC-ONLY, non-transmitting bridge to byte-exact Frozen Capital v5.

This process never opens Excel, brokers, exchanges or URLs.  It does not
establish real-time eligibility: upstream Frozen No.1.1 decision and exact
live-arrival proof do not yet exist. Input is a bounded SYNTHETIC fixture.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import math
import pathlib
import re
import sys
from decimal import Decimal, InvalidOperation

FROZEN_NO11 = '10c94c92c4bd2a59a22744667fd0210252602df4'
CAPITAL_AUTHORITY = '710656491be06235901b45c50a8b5cbd714ba4eb'
CAPITAL_BLOBS = {
    'allocation.py': 'c48283ead2c1dc369281c734ee2006d1ea479fac',
    'execution.py': '311fa97b4dccf5ce74af5a81e17d39c986c97573',
    'slot_policy.py': '094e6e798d2884321be67316b7b3342bc048f03a',
}
SOURCE = pathlib.Path(__file__).resolve().parents[1] / 'frozen-capital-v5'


class Blocked(Exception):
    pass


def require(test: bool, label: str) -> None:
    if not test:
        raise Blocked(label)


def git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(content)).encode('ascii') + b'\0' + content).hexdigest()


def load_frozen():
    for filename, expected in CAPITAL_BLOBS.items():
        path = SOURCE / filename
        require(path.is_file() and not path.is_symlink(), 'FROZEN_CAPITAL_SOURCE_MISSING')
        require(git_blob_sha(path.read_bytes()) == expected, 'FROZEN_CAPITAL_SOURCE_HASH_MISMATCH')
    sys.path.insert(0, str(SOURCE))
    # Do not modify/copy V5 decision logic: call the original audited Python.
    allocation = importlib.import_module('allocation')
    slots = importlib.import_module('slot_policy')
    require(str(allocation.BUY) == '1.0005', 'BUY_COST_CONTRACT_MISMATCH')
    return allocation, slots


def jpy(value, label: str) -> Decimal:
    require(isinstance(value, (int, float, str)) and not isinstance(value, bool), label)
    try:
        money = Decimal(str(value))
    except InvalidOperation as exc:
        raise Blocked(label) from exc
    require(money.is_finite() and money >= 0, label)
    return money


def symbol(value, label):
    require(isinstance(value, str), label)
    raw = value.strip().upper()
    require(re.fullmatch(r'[0-9A-Z]{4}(?:\.T)?', raw) is not None, label)
    return raw if raw.endswith('.T') else raw + '.T'


def funds(inputs):
    require(isinstance(inputs, dict) and set(inputs) == {'cash', 'equity', 'exposure'},
            'CAPITAL_INPUT_SHAPE_INVALID')
    cash = jpy(inputs['cash'], 'CASH_INVALID')
    equity = jpy(inputs['equity'], 'EQUITY_INVALID')
    exposure = jpy(inputs['exposure'], 'EXPOSURE_INVALID')
    require(equity == cash + exposure, 'ARK_EQUITY_CASH_EXPOSURE_MISMATCH')
    return cash, equity, exposure


def _unique_symbols(values, label):
    require(isinstance(values, list) and len(values) <= 500, label + '_ARRAY_INVALID')
    normalized = [symbol(value, label + '_SYMBOL_INVALID') for value in values]
    require(len(set(normalized)) == len(normalized), label + '_DUPLICATES')
    return set(normalized)


def shadow(request):
    require(isinstance(request, dict), 'REQUEST_OBJECT_REQUIRED')
    require(request.get('schemaId') == 'ARK_NO11_FROZEN_V5_SYNTHETIC_BRIDGE_V1',
            'SYNTHETIC_SCHEMA_REQUIRED')
    require(request.get('evidenceMode') == 'SYNTHETIC_OFFLINE_ONLY',
            'LIVE_DECISION_SOURCE_NOT_CERTIFIED')
    require(request.get('strategyFreezeCommit') == FROZEN_NO11,
            'NO11_FREEZE_MISMATCH')
    require(request.get('capitalAuthorityCommit') == CAPITAL_AUTHORITY,
            'CAPITAL_AUTHORITY_MISMATCH')
    require(request.get('afterFirstLegalSellFill') is False,
            'AFTER_FIRST_SELL_FILL_NO_NEW_BUY')
    require(request.get('pendingBrokerOrders') is False,
            'PENDING_ORDERS_BLOCK_FUNDING')
    require(request.get('sessionVerified') is False,
            'SESSION_CERTIFICATION_NOT_ALLOWED_IN_SYNTHETIC')

    cash, equity, exposure = funds(request.get('arkCapitalInputs'))
    external = _unique_symbols(request.get('externalSymbols'), 'PERSONAL')
    managed = _unique_symbols(request.get('arkManagedSymbols'), 'ARK_MANAGED')
    require(not external.intersection(managed), 'PERSONAL_AND_ARK_OVERLAP')
    require(len(managed) <= 3, 'ARK_MAX3_EXCEEDED')
    existing_bands = request.get('existingBands')
    require(isinstance(existing_bands, list) and len(existing_bands) == len(managed)
            and all(b in ('S', 'A', 'B') for b in existing_bands),
            'FROZEN_EXISTING_BAND_ATTESTATION_MISSING')
    if managed:
        require(exposure > 0, 'ARK_MARK_TO_MARKET_REQUIRED')
    else:
        require(exposure == 0, 'ARK_EXPOSURE_WITHOUT_MANAGED_POSITIONS')

    minute = request.get('minute')
    require(type(minute) is int and 540 <= minute < 920,
            'FROZEN_ENTRY_TIME_INVALID')
    candidates = request.get('preorderedCandidates')
    require(isinstance(candidates, list) and len(candidates) <= 20,
            'CANDIDATE_BATCH_INVALID')
    tables = request.get('syntheticTrainingTables')
    require(isinstance(tables, dict), 'SYNTHETIC_ARRIVAL_TABLE_REQUIRED')
    candidate_ids = set()
    candidate_symbols = set()
    eligible = []
    rejected = []
    allocation, slot = load_frozen()
    for candidate in candidates:
        require(isinstance(candidate, dict), 'CANDIDATE_INVALID')
        eid = candidate.get('entry_id')
        require(isinstance(eid, str) and eid and eid not in candidate_ids,
                'CANDIDATE_ENTRY_ID_INVALID_OR_DUPLICATED')
        candidate_ids.add(eid)
        sym = symbol(candidate.get('brokerSymbol'), 'CANDIDATE_SYMBOL_INVALID')
        require(sym not in candidate_symbols, 'DUPLICATE_CANDIDATE_SYMBOL')
        candidate_symbols.add(sym)
        require(sym not in external, 'PERSONAL_SYMBOL_BUY_PROHIBITED')
        require(sym not in managed, 'ARK_SYMBOL_ALREADY_OWNED')
        score = candidate.get('capital_score')
        ml = candidate.get('ML')
        require(isinstance(score, (int, float)) and not isinstance(score, bool)
                and math.isfinite(score) and score >= 1.0,
                'FROZEN_CAPITAL_SCORE_INVALID')
        require(isinstance(ml, (int, float)) and not isinstance(ml, bool)
                and math.isfinite(ml) and ml >= 1.0,
                'FROZEN_ML_INVALID')
        require(candidate.get('rank') in ('S', 'A', 'B'), 'FROZEN_RANK_INVALID')
        block = candidate.get('block')
        require(isinstance(block, (str, int)) and not isinstance(block, bool),
                'FROZEN_BLOCK_REQUIRED')
        table = tables.get(str(block))
        require(isinstance(table, dict), 'FROZEN_ARRIVAL_TABLE_MISSING')
        price = jpy(candidate.get('raw_reference'), 'REFERENCE_PRICE_INVALID')
        require(price > 0, 'REFERENCE_PRICE_INVALID')
        # A candidate passed to this bridge is explicitly synthetic. The real
        # Frozen Selector/Entry certification is NOT emulated here.
        occupancy = len(managed) + len(eligible)
        if occupancy >= 3:
            rejected.append({'entry_id': eid, 'reason': 'MAX_POSITION_CAP'})
            continue
        try:
            admitted, reason, _audit = slot.gate(candidate, occupancy, minute, table)
        except (KeyError, AssertionError, TypeError, IndexError, ZeroDivisionError) as exc:
            raise Blocked('FROZEN_SLOT_SOURCE_INPUT_INVALID') from exc
        if not admitted:
            rejected.append({'entry_id': eid, 'reason': reason})
            continue
        eligible.append(candidate)

    assigned = allocation.allocation(eligible, str(equity), str(exposure),
                                     str(cash), existing_bands) if eligible else []
    spent = sum((a['debit'] for a in assigned), Decimal('0'))
    require(spent <= cash, 'FROZEN_ALLOCATOR_EXCEEDED_BUYING_POWER')
    require(len(managed) + sum(a['quantity'] > 0 for a in assigned) <= 3,
            'FROZEN_ALLOCATOR_EXCEEDED_MAX3')
    for candidate, output in zip(eligible, assigned):
        q = output['quantity']
        require(type(q) is int and q >= 0 and q % 100 == 0,
                'FROZEN_ALLOCATOR_INVALID_LOT')
        fee_cost = Decimal(str(candidate['raw_reference'])) * allocation.BUY
        require(output['debit'] == fee_cost * q,
                'FROZEN_ALLOCATOR_DEBIT_MISMATCH')
        require(output['debit'] <= output['equity_cap'],
                'FROZEN_ALLOCATOR_BAND_CAP_EXCEEDED')
    return {
        'schemaId': 'ARK_NO11_FROZEN_CAPITAL_V5_OFFLINE_RESULT_V1',
        'status': 'SYNTHETIC_SHADOW_ONLY',
        'strategyFreezeCommit': FROZEN_NO11,
        'capitalAuthorityCommit': CAPITAL_AUTHORITY,
        'inputCashJpy': str(cash), 'inputEquityJpy': str(equity),
        'arkExposureJpy': str(exposure), 'allocatedDebitJpy': str(spent),
        'remainingBuyingPowerJpy': str(cash - spent),
        'admittedCount': len(eligible),
        'fundedCount': sum(a['quantity'] > 0 for a in assigned),
        'rejected': rejected,
        'allocations': [{'entry_id': a['entry_id'], 'quantity': a['quantity'],
                         'band': a['band'], 'debitJpy': str(a['debit']),
                         'batchBudgetJpy': str(a['batch_budget']),
                         'firstPassQuantity': a['first_pass_quantity'],
                         'waterFillLots': a['water_fill_lots']} for a in assigned],
        'externalHoldingsIncludedInEquity': False,
        'personalStockDoubleDeducted': False,
        'liveFeedTimestampCertified': False, 'frozenEntryCertified': False,
        'orderAllowed': False, 'rssOrderFunctionAllowed': False,
        'transmitted': False, 'productionReady': False,
    }


def main():
    try:
        request = json.load(sys.stdin)
        result = shadow(request)
        json.dump(result, sys.stdout, ensure_ascii=False, separators=(',', ':'))
        sys.stdout.write('\n')
    except (Blocked, AssertionError, ValueError, TypeError, KeyError) as exc:
        # Only redact errors: fixtures can contain broker identity and balances.
        reason = str(exc) if isinstance(exc, Blocked) else 'FROZEN_ALLOCATOR_INVALID_INPUT'
        print(json.dumps({'status': 'BLOCKED', 'reason': reason,
                          'orderAllowed': False, 'transmitted': False}), file=sys.stdout)
        sys.exit(2)


if __name__ == '__main__':
    main()
