#!/usr/bin/env python3
"""Workbook-location migration, never market evidence or order authorization.

The operator explicitly applies registration for the three open role-checked
books. Normal runtime still requires that exact registration. Completed nightly
pointers/checkpoints stay byte-identical; an approved morning run may derive a
new immutable handoff with ONLY orderIdWorkbookPath changed to the registered
location. Dates, prices, selected symbols and review/authorization flags do not
change. The original handoff and receipts are never overwritten.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import tempfile

MARK = 'ARK_NO11_REGISTERED_OPEN_BOOK_HANDOFF_PATH_V2'
ROLES = {'Account': ('accountWorkbookPath', 'ARK_ACCOUNT_READONLY'),
         'Market': ('marketWorkbookPath', 'ARK_MARKET_READONLY'),
         'OrderIds': ('orderIdWorkbookPath', 'ARK_ORDER_IDS_READONLY')}


def need(ok, code):
    if not ok:
        raise ValueError('NO11_LIVE_BOOK_PATH_' + code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(obj):
    return (json.dumps(obj, ensure_ascii=False, separators=(',', ':'),
                       allow_nan=False) + '\n').encode('utf-8')


def read(path):
    path = Path(path)
    need(path.is_absolute() and path.is_file() and not path.is_symlink(), 'SOURCE_MISSING')
    need(0 < path.stat().st_size < 20000000, 'SOURCE_SIZE')
    raw = path.read_bytes()
    def unique(items):
        result = {}
        for key, value in items:
            need(key not in result, 'DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    obj = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique)
    need(type(obj) is dict, 'JSON_OBJECT')
    return obj, raw


def registry_paths(record):
    """Validate previous enrollment structurally, even if it has been moved.

    Actual open files are separately checked by the existing COM resolver and
    checked_registration. A stale enrollment must not require the old location
    to keep existing just to register the new one.
    """
    need(type(record) is dict and
         record.get('schemaId') == 'ARK_NO11_DATA_WORKBOOK_REGISTRATION_V1' and
         record.get('orderTransmission') is False, 'REGISTRY')
    rows = record.get('books')
    need(type(rows) is list and len(rows) == 3, 'THREE_REGISTRY_BOOKS')
    result = {}
    names = set()
    for row in rows:
        need(type(row) is dict and row.get('role') in ROLES and
             row['role'] not in result, 'REGISTRY_ROLE')
        p = row.get('path')
        need(type(p) is str and Path(p).is_absolute() and
             Path(p).suffix.lower() in ('.xlsx', '.xlsb', '.xlsm') and
             row.get('name') == Path(p).name and
             row.get('sheet') == ROLES[row['role']][1] and
             row.get('date1904') is False and
             Path(p).name.casefold() not in names, 'REGISTERED_PATH')
        names.add(Path(p).name.casefold())
        result[row['role']] = p
    need(len({os.path.normcase(p) for p in result.values()}) == 3, 'DISTINCT_PATHS')
    return result


def make_registration(paths, previous, settings, source_sha):
    previous_paths = registry_paths(previous)
    allowed = list(previous.get('previousOrderIdWorkbookPaths', []))
    allowed += [previous_paths['OrderIds'], settings['orderIdWorkbookPath']]
    allowed = list(dict.fromkeys(p for p in allowed if type(p) is str and p))
    return {'schemaId': 'ARK_NO11_DATA_WORKBOOK_REGISTRATION_V1',
            'books': [{'role': role, 'path': paths[role],
                       'name': Path(paths[role]).name, 'sheet': sheet,
                       'date1904': False}
                      for role, (_, sheet) in ROLES.items()],
            'sourceRegistrationSha256': source_sha,
            'previousOrderIdWorkbookPaths': allowed,
            'registrationReason': 'EXPLICIT_INSTALL_CURRENT_OPEN_THREE_BOOKS',
            'orderTransmission': False}


def same_locations(a, b):
    return set(a) == set(b) and all(
        os.path.normcase(os.path.abspath(a[key])) ==
        os.path.normcase(os.path.abspath(b[key])) for key in a)


def immutable(path, raw):
    """Publish independent bytes; never hard-link a market source file."""
    path = Path(path)
    need(path.parent.is_dir() and not path.is_symlink(), 'OUTPUT_LOCATION')
    if path.exists():
        need(path.read_bytes() == raw, 'IMMUTABLE_OUTPUT_CHANGED')
        return path
    temp = None
    try:
        with tempfile.NamedTemporaryFile('wb', dir=path.parent,
                prefix='.book-path-', delete=False) as stream:
            temp = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temp, path)
        except FileExistsError:
            need(not path.is_symlink() and path.read_bytes() == raw, 'OUTPUT_RACE')
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    return path


def rebind_handoff(binding, today):
    record, rb = read(binding['dataWorkbookRegistration'])
    need(digest(rb) == binding['dataWorkbookRegistrationSha256'], 'REGISTRATION_HASH')
    paths = registry_paths(record)
    settings, _ = read(binding['settings'])
    need(settings.get('orderTransmission') is False and
         settings.get('automaticOrderAuthorization') is False and
         settings.get('sameDayApprovalRequired') is True and
         settings.get('normalMaxPositions') == 3 and
         all(settings.get(field) == paths[role]
             for role, (field, _) in ROLES.items()), 'SETTINGS_REGISTRATION_DIFFER')
    source = Path(binding['handoff'])
    hand, raw = read(source)
    need(digest(raw) == binding['handoffSha256'] and
         source.name == 'morning-handoff-' + digest(raw) + '.json' and
         hand.get('schemaId') == 'ARK_NO11_MORNING_MASTER_HANDOFF_V1' and
         hand.get('sessionDate') == binding.get('sessionDate') == today and
         hand.get('orderTransmission') is False and
         hand.get('productionReady') is False and
         hand.get('datedMasterCreated') is False and
         hand.get('reviewStatus') == 'NOT_REVIEWED', 'HANDOFF_CONTRACT')
    target = paths['OrderIds']
    if hand.get('orderIdWorkbookPath') == target:
        return binding
    need(hand.get('orderIdWorkbookPath') in
         record.get('previousOrderIdWorkbookPaths', []), 'UNREGISTERED_OLD_ORDER_PATH')
    # Source pins and every non-location field remain exact; do not invent a
    # reviewed master, promote a date or recollect any saved market receipt.
    pins, spec = hand.get('sourcePins'), hand.get('spec')
    need(type(pins) is dict and set(pins) ==
         {'chartReceipt', 'passMask', 'previousStage'} and type(spec) is dict,
         'HANDOFF_SOURCE_PINS')
    for key, sha in pins.items():
        _, data = read(spec[key])
        need(digest(data) == sha, 'HANDOFF_SOURCE_CHANGED')
    revised = dict(hand, orderIdWorkbookPath=target)
    updated = encode(revised)
    dest = immutable(source.parent / ('morning-handoff-' + digest(updated) + '.json'), updated)
    need(source.read_bytes() == raw, 'ORIGINAL_HANDOFF_CHANGED')
    print('NO11_LIVE_HANDOFF_WORKBOOK_PATH=REGISTERED_OPEN_BOOK')
    print('NO11_LIVE_HANDOFF_MARKET_DATA_RECAPTURED=False')
    return dict(binding, handoff=str(dest), handoffSha256=digest(updated))


HOOK = '''    # ARK_NO11_REGISTERED_OPEN_BOOK_HANDOFF_PATH_V2
    path_tool = safe(binding['liveWorkbookHandoffTool'])
    need(digest(path_tool.read_bytes()) == binding['liveWorkbookHandoffToolSha256'],
         'LIVE_BOOK_PATH_TOOL_CHANGED')
    path_spec = importlib.util.spec_from_file_location('ark_registered_book_handoff', path_tool)
    path_module = importlib.util.module_from_spec(path_spec)
    path_spec.loader.exec_module(path_module)
    binding = path_module.rebind_handoff(binding, now()[:10])
'''


def transform_bridge(raw):
    bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw.decode('utf-8-sig')
    newline = '\r\n' if '\r\n' in text else '\n'
    src = text.replace('\r\n', '\n')
    if MARK in src:
        need(src.count(HOOK) == 1, 'PARTIAL_BRIDGE_HOOK')
        return raw
    anchor = '    binding = resolve_daily_binding(binding, now()[:10])\n'
    need(src.count(anchor) == 1 and
         "need(same_day_operator_approved is True, 'SAME_DAY_OPERATOR_APPROVAL_REQUIRED')" in src,
         'BRIDGE_SOURCE_CHANGED')
    revised = src.replace(anchor, anchor + HOOK, 1)
    compile(revised, 'registered_book_bridge.py', 'exec')
    return (b'\xef\xbb\xbf' if bom else b'') + revised.replace('\n', newline).encode('utf-8')
