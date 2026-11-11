"""Permanent read-only OneClick presentation, never a trading permission source.

Use the existing authorization inspector unchanged. Add independent display
fields for the wall-clock window, reservation history, recorded run result,
verified prepared data, and source-repair receipt. No Excel/process/order I/O.
All strings for Windows PowerShell travel as ASCII JSON Unicode escapes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

JST = timezone(timedelta(hours=9))
SCHEMA = 'ARK_NO11_ONECLICK_PRESENTATION_V2'
CONTRACT = 'ARK_NO11_ONECLICK_DISPLAY_INSTALL_V2'
LEGACY_BLOB = '1f5611336abc8d68731a44243fa67a6c6a4ebf9f'
DAY = re.compile(r'20\d{2}-\d{2}-\d{2}\Z')
CODE = re.compile(r'(?:NO11|P1_RSS|P1_FORWARD)_[A-Z0-9_]{1,160}\Z')
BUTTONS = {'trade': 'START TRADING / MAX3', 'nightly': 'UPDATE DATA / 翌日準備',
           'refresh': 'REFRESH / 状態更新', 'review': 'REVIEW / 停止を確認',
           'logs': 'LOGS / ログ'}


def safe(path, *, root=None, directory=False):
    p = Path(path)
    if not p.is_absolute():
        raise ValueError('DISPLAY_PATH_UNVERIFIED')
    for q in (p, *p.parents):
        if q.exists() or q.is_symlink():
            if q.is_symlink() or getattr(q.lstat(), 'st_file_attributes', 0) & 1024:
                raise ValueError('DISPLAY_PATH_UNVERIFIED')
    if not (p.is_dir() if directory else p.is_file()):
        raise ValueError('DISPLAY_SOURCE_MISSING')
    if root is not None and not p.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError('DISPLAY_PATH_UNVERIFIED')
    return p


def load(path, *, root=None):
    p = safe(path, root=root)
    raw = p.read_bytes()
    if not 0 < len(raw) <= 4_000_000:
        raise ValueError('DISPLAY_SOURCE_SIZE')
    def unique(rows):
        value = {}
        for key, item in rows:
            if key in value:
                raise ValueError('DISPLAY_DUPLICATE_KEY')
            value[key] = item
        return value
    value = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique)
    if type(value) is not dict:
        raise ValueError('DISPLAY_OBJECT')
    return value


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, safe(path))
    item = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(item)
    return item


def native_inspector():
    home = Path(__file__).resolve().parent
    contract = load(home / 'oneclick-display-v2.contract.json', root=home)
    legacy = safe(home / 'oneclick_status.py', root=home)
    if (contract.get('schemaId') != CONTRACT or contract.get('orderTransmission') is not False
            or contract.get('displaySha256') != sha(Path(__file__).read_bytes())
            or contract.get('legacyStatusSha256') != sha(legacy.read_bytes())):
        raise ValueError('DISPLAY_DEPENDENCY_CHANGED')
    raw = legacy.read_bytes().decode('utf-8-sig').replace('\r\n', '\n').encode('utf-8')
    if hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != LEGACY_BLOB:
        raise ValueError('DISPLAY_LEGACY_UNKNOWN')
    return module(legacy, 'ark_native_oneclick_status_v2').inspect


def reservation(store, day, now):
    request = Path(store) / ('PREOPEN-' + day + '.request.json')
    used = Path(store) / ('PREOPEN-' + day + '.execution-claimed')
    trade = Path(store) / ('TRADE-' + day + '.launch.json')
    result = {'state': 'NONE', 'tradeRequested': False}
    try:
        if trade.exists():
            t = load(trade, root=store)
            if t.get('schemaId') != 'ARK_NO11_UNIFIED_START_REQUEST_V1' or t.get('kind') != 'TRADE' or t.get('asOfDate') != day:
                raise ValueError('TRADE_RECEIPT_INVALID')
            result['tradeRequested'] = True
        if not request.exists():
            if used.exists():
                raise ValueError('ORPHAN_PREOPEN_CLAIM')
            return result
        r = load(request, root=store)
        nonce = r.get('nonce')
        issued = datetime.fromisoformat(r['requestedAtJst'])
        if (r.get('schemaId') != 'ARK_NO11_PREOPEN_STANDBY_REQUEST_V1'
                or r.get('sessionDate') != day or r.get('sameDayExplicitOrderApproval') is not True
                or r.get('tradeLaunchedAtArm') is not False or r.get('orderTransmissionAtArm') is not False
                or type(nonce) is not str or not re.fullmatch(r'[a-f0-9]{32}', nonce)
                or issued.utcoffset() != timedelta(hours=9) or issued.date().isoformat() != day
                or not '08:30:00' <= issued.strftime('%H:%M:%S') < '09:00:00'
                or issued > now or r.get('earliestTradeStartJst') != day + 'T09:00:00+09:00'
                or r.get('expiresAtJst') != day + 'T09:02:00+09:00'):
            raise ValueError('PREOPEN_RECEIPT_INVALID')
        if used.exists():
            content = safe(used, root=store).read_text(encoding='utf-8-sig').strip()
            if content != 'PREOPEN_SINGLE_LAUNCH_ATTEMPT_CLAIMED|' + day + '|' + nonce:
                raise ValueError('PREOPEN_CLAIM_INVALID')
            result['state'] = 'ATTEMPT_RECORDED'
        elif now.strftime('%H:%M:%S') >= '09:02:00':
            result['state'] = 'EXPIRED'
        else:
            result['state'] = 'RESERVED_RECORD'
    except (ValueError, TypeError, KeyError, OSError):
        result['state'] = 'UNVERIFIED'
    return result


def run_evidence(settings, day):
    result = {'state': 'NO_RECORD', 'collector': 'UNKNOWN', 'reason': None}
    try:
        boot = load(settings['bootstrapConfigFile'])
        root = safe(boot['privateRoot'], directory=True)
        pointer = root / ('received-session-' + day + '.active.json')
        if not pointer.exists():
            return result
        p = load(pointer, root=root)
        run = safe(p['runRoot'], root=root, directory=True)
        if (p.get('schemaId') != 'ARK_NO11_RECEIVED_ACTIVE_RUN_V1'
                or p.get('sessionDate') != day or run.parent != root
                or not re.fullmatch('session-' + re.escape(day) + '-[a-f0-9]{32}', run.name)):
            raise ValueError('RUN_SCOPE')
        result['state'] = 'REGISTERED'
        attempts = sorted(run.glob('attempt-*'))
        if len(attempts) > 16:
            raise ValueError('ATTEMPT_LIMIT')
        last_time = None
        if attempts:
            a_path = attempts[-1] / 'attempt.json'
            a = load(a_path, root=run)
            state = a.get('status')
            result['collector'] = state if state in ('CLOSED', 'CONNECTED', 'RUNNING', 'REQUESTING') else 'UNKNOWN'
            last_time = a_path.stat().st_mtime_ns
            if state == 'CLOSED':
                result['state'] = 'COLLECTOR_CLOSED_RECORD'
        failure = run / 'controller-failure.json'
        if failure.exists():
            f = load(failure, root=run)
            code = f.get('reason')
            result['reason'] = code if type(code) is str and CODE.fullmatch(code) else 'UNCLASSIFIED'
            # A historical failure is not proof that a resumed attempt failed.
            if result['collector'] == 'CLOSED' or last_time is None or failure.stat().st_mtime_ns >= last_time:
                result['state'] = 'FAILURE_RECORDED'
            else:
                result['previousFailure'] = True
    except (OSError, ValueError, TypeError, KeyError):
        result['state'] = 'UNVERIFIED'
    return result


def prepared_data(binding_file, binding, now):
    result = {'state': 'UNVERIFIED', 'target': None, 'count': None, 'weekly': 'UNVERIFIED'}
    try:
        resume = safe(binding['nightlyResumeTool'])
        tool = safe(resume.with_name('no11_selection_status.py'))
        pin = binding.get('nightlyResumeValidatorSha256')
        if type(pin) is not str or not re.fullmatch(r'[a-f0-9]{64}', pin) or sha(tool.read_bytes()) != pin:
            raise ValueError('VALIDATOR_HASH')
        info = module(tool, 'ark_selection_display_v2').inspect(Path(binding_file), at=now)
        if info.get('schemaId') != 'ARK_NO11_SELECTION_DISPLAY_V1' or info.get('orderTransmission') is not False or info.get('readOnly') is not True:
            raise ValueError('SELECTION_CONTRACT')
        daily = info['daily']
        state = daily.get('state')
        result['state'] = state if state in ('READY', 'NOT_READY', 'INVALID', 'UNVERIFIED') else 'UNVERIFIED'
        target = daily.get('target')
        if target is not None:
            if type(target) is not str or not DAY.fullmatch(target) or datetime.fromisoformat(target).date() < now.date():
                raise ValueError('DATA_DATE')
            result['target'] = target
        if state == 'READY':
            if target is None or type(daily.get('count')) is not int or not 1 <= daily['count'] <= 47:
                raise ValueError('DATA_COUNT')
            result['count'] = daily['count']
        result['weekly'] = info['weekly'].get('state', 'UNVERIFIED')
    except (OSError, ValueError, TypeError, KeyError, ImportError):
        result['state'] = 'UNVERIFIED'
    return result


def repair_evidence(store, binding):
    path = Path(store) / 'afterclose-source-repair-v1-install.json'
    if not path.exists():
        return 'NOT_VERIFIED'
    try:
        r = load(path, root=store)
        checksum = r.pop('checkpointSha256', None)
        raw = (json.dumps(r, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n').encode()
        if checksum != sha(raw) or r.get('kind') != 'ARK_NO11_AFTERCLOSE_SOURCE_REPAIR_V1' or r.get('orderTransmission') is not False:
            raise ValueError('REPAIR_RECEIPT')
        if r.get('phase') == 'PREPARED':
            return 'INCOMPLETE'
        if r.get('phase') != 'COMPLETE':
            raise ValueError('REPAIR_PHASE')
        engine = safe(binding['engine'], directory=True)
        targets = {'BOOTSTRAP': 'tools/no11_received_session_bootstrap.py', 'FUNDING': 'tools/no11_rss_buying_power.py'}
        if set(r['entries']) != set(targets):
            raise ValueError('REPAIR_TARGETS')
        for key, rel in targets.items():
            entry = r['entries'][key]
            expected = safe(engine / rel, root=engine)
            if Path(entry['path']) != expected or sha(expected.read_bytes()) != entry['afterSha256']:
                raise ValueError('REPAIR_CHANGED')
        return 'APPLIED'
    except (OSError, ValueError, TypeError, KeyError):
        return 'UNVERIFIED'


def present(state, now, reserved, run, data, repair):
    """Pure state-to-copy reducer. Never modifies native permission fields."""
    day, tm = now.date().isoformat(), now.strftime('%H:%M:%S')
    if now.utcoffset() != timedelta(hours=9):
        raise ValueError('JST_REQUIRED')
    if state.get('reason') == 'NON_TRADING_DAY':
        phase, label = 'NO_SESSION', 'NO SESSION / 受付対象外'
    elif tm >= '18:00:00':
        phase, label = 'AFTER_CLOSE', 'CLOSED / 本日終了'
    elif tm >= '15:20:00':
        phase, label = 'ENTRY_CLOSED', 'ENTRY CLOSED / 新規受付終了'
    elif tm < '08:30:00':
        phase, label = 'BEFORE_OPEN', 'BEFORE OPEN / 時間外'
    elif tm < '09:00:00':
        phase, label = 'PREOPEN', 'PREOPEN / 開場前'
    else:
        phase, label = 'SESSION', 'SESSION / 受付時間内'
    rs = run.get('state')
    if rs == 'FAILURE_RECORDED':
        trading = 'STOPPED / 停止記録・要確認'
    elif rs == 'UNVERIFIED' or reserved.get('state') == 'UNVERIFIED':
        trading = 'UNVERIFIED / 記録を確認'
    elif rs == 'COLLECTOR_CLOSED_RECORD':
        trading = 'COLLECTOR CLOSED / 収集終了記録'
    elif rs == 'REGISTERED':
        trading = 'RUN RECORDED / 稼働未確認'
    elif reserved.get('tradeRequested') or reserved.get('state') == 'ATTEMPT_RECORDED':
        trading = 'START REQUESTED / 稼働未確認'
    elif reserved.get('state') == 'RESERVED_RECORD' and phase in ('PREOPEN', 'SESSION') and tm < '09:02:00':
        trading = 'RESERVED 09:00 / 当日・稼働未確認'
    elif reserved.get('state') in ('EXPIRED', 'RESERVED_RECORD'):
        trading = 'RESERVATION ENDED / 予約履歴'
    elif state.get('canRequestTrade') is True:
        trading = 'AWAITING APPROVAL / 当日承認待ち'
    else:
        trading = 'NOT REQUESTED / 当日起動記録なし'
    target = data.get('target')
    scope = 'TODAY' if target == day else 'NEXT'
    if data.get('state') == 'READY' and target:
        status = 'READY' if data.get('weekly') == 'DONE' else 'DAILY READY / WEEKLY要確認'
        data_line = f"{scope} {target[5:].replace('-', '/')} {status} {data['count']}銘柄"
    elif data.get('state') == 'NOT_READY':
        data_line = 'NOT READY / 準備未確認'
    else:
        data_line = 'UNVERIFIED / データ要確認'
    check = {'APPLIED': 'SOURCE FIX APPLIED / 適用済み', 'INCOMPLETE': 'INSTALL INCOMPLETE / 起動しない',
             'UNVERIFIED': 'SOURCE FIX UNVERIFIED / 要確認', 'NOT_VERIFIED': 'SOURCE FIX / 適用未確認'}[repair]
    text = '\n'.join((f'TODAY {day} | {label}', f'TRADING {trading}', f'DATA {data_line}', f'CHECK {check}'))
    details = '\n'.join((f'Checked: {now.isoformat(timespec="seconds")}',
        f'Native status: {state.get("mode", "UNVERIFIED")} / {state.get("reason", "UNVERIFIED")}',
        f'Reservation record: {reserved.get("state")}', f'Run record: {rs}',
        f'Collector record: {run.get("collector", "UNKNOWN")}', f'Failure code: {run.get("reason") or "NONE"}',
        '表示は保存済み証跡です。稼働・実発注・約定の確認ではありません。',
        '予約と承認は当日限り。翌日に持ち越しません。', '操作可否は既存の安全判定に従います。'))
    return {'schemaId': SCHEMA, 'phase': phase, 'trading': trading, 'data': data,
            'repair': repair, 'text': text, 'details': details, 'buttons': dict(BUTTONS),
            'readOnly': True, 'liveVerified': False, 'orderTransmission': False}


def inspect(settings_file, binding_file, *, at=None, native=None):
    now = at or datetime.now(JST)
    original = native or native_inspector()
    state = original(settings_file, binding_file, at=now)
    if state.get('schemaId') != 'ARK_NO11_ONECLICK_STATUS_V1' or state.get('readOnly') is not True or state.get('brokerOrderTransmission') is not False:
        raise ValueError('NATIVE_STATUS_CONTRACT')
    settings, binding = load(settings_file), load(binding_file)
    store = Path(settings_file).parent
    state = dict(state)
    state['presentation'] = present(state, now, reservation(store, now.date().isoformat(), now),
        run_evidence(settings, now.date().isoformat()), prepared_data(binding_file, binding, now),
        repair_evidence(store, binding))
    return state


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--settings', type=Path, required=True)
    p.add_argument('--binding', type=Path, required=True)
    args = p.parse_args(argv)
    try:
        result = inspect(args.settings, args.binding)
        code = 0
    except (OSError, ValueError, KeyError, TypeError, ImportError):
        result = {'schemaId': 'ARK_NO11_ONECLICK_STATUS_V1', 'mode': 'BLOCKED',
                  'reason': 'DISPLAY_SOURCE_UNVERIFIED', 'canRequestTrade': False,
                  'canRunNightly': False, 'readOnly': True, 'brokerOrderTransmission': False}
        code = 2
    print(json.dumps(result, ensure_ascii=True, separators=(',', ':'), allow_nan=False))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
