"""Persistently bind the optional read-only account source. No brokerage writes."""
import json
import os
from pathlib import Path
import re
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[3]
ENV = 'ARK_NO11_ACCOUNT_OBSERVATION_FILE'
NODE = Path(__file__).with_suffix('.mjs')


def private(value):
    p = Path(value)
    if (not p.is_absolute() or p == ROOT or ROOT in p.parents or p.is_symlink()
            or any(x.is_symlink() for x in p.parents) or not p.parent.is_dir()):
        raise ValueError('NO11_ACCOUNT_PATH_INVALID')
    return p


def write(path, value):
    p = private(path)
    temp = p.with_name(p.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('x', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, sort_keys=True, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, p)
    finally:
        if temp.exists():
            temp.unlink()


class AccountObservation:
    def __init__(self, root, session):
        self.root, self.session = Path(root).absolute(), session
        self.enabled, self.source, self.error = False, None, None
        self.report = {'status': 'NOT_CONFIGURED', 'newShadowEntriesAllowed': False,
                       'excludedSymbols': [], 'productionReady': False, 'orderTransmission': False}
        binding = self.root / 'account-observer-binding.json'
        supplied = os.environ.get(ENV)
        try:
            private(binding)
            if binding.exists():
                self.enabled = True
                if not binding.is_file() or not 0 < binding.stat().st_size <= 100000:
                    raise ValueError('NO11_ACCOUNT_BINDING_INVALID')
                saved = json.loads(binding.read_text(encoding='utf-8'))
                if (saved.get('schemaId') != 'ARK_NO11_ACCOUNT_BINDING_V1'
                        or saved.get('sessionDate') != session or saved.get('orderTransmission') is not False):
                    raise ValueError('NO11_ACCOUNT_BINDING_INVALID')
                self.source = str(private(saved['source']))
                if supplied is not None and str(private(supplied)) != self.source:
                    raise ValueError('NO11_ACCOUNT_BINDING_CHANGED')
            elif supplied is not None:
                self.enabled = True
                self.source = str(private(supplied))
                write(binding, {'schemaId': 'ARK_NO11_ACCOUNT_BINDING_V1', 'sessionDate': session,
                                'source': self.source, 'orderTransmission': False})
        except (OSError, ValueError, TypeError, KeyError):
            self.enabled, self.error = True, 'NO11_ACCOUNT_BINDING_UNAVAILABLE'

    def observe(self):
        if not self.enabled:
            return self.report
        try:
            if self.error:
                raise ValueError(self.error)
            r = subprocess.run(['node', str(NODE), '--source', self.source, '--state',
                str(self.root / 'account-observation-state.json'), '--session', self.session],
                capture_output=True, text=True, encoding='utf-8', timeout=10, check=False)
            obj = json.loads(r.stdout)
            if (r.returncode not in (0, 2) or obj.get('schemaId') != 'ARK_NO11_ACCOUNT_OBSERVATION_REPORT_V1'
                    or obj.get('productionReady') is not False or obj.get('orderTransmission') is not False
                    or type(obj.get('newShadowEntriesAllowed')) is not bool
                    or type(obj.get('excludedSymbols')) is not list
                    or any(type(s) is not str or not re.fullmatch(r'[0-9A-Z]{4}\.T', s) for s in obj['excludedSymbols'])
                    or r.returncode != 0 and obj['newShadowEntriesAllowed']):
                raise ValueError('NO11_ACCOUNT_INSPECTOR_OUTPUT_INVALID')
            self.report = obj
        except (OSError, ValueError, TypeError, subprocess.SubprocessError):
            self.report = {'status': 'BLOCKED', 'blockers': [self.error or 'NO11_ACCOUNT_SOURCE_UNAVAILABLE'],
                          'newShadowEntriesAllowed': False, 'excludedSymbols': [],
                          'productionReady': False, 'orderTransmission': False}
        try:
            write(self.root / 'account-observation-latest-report.json', self.report)
        except (OSError, ValueError):
            self.report = dict(self.report, status='BLOCKED', newShadowEntriesAllowed=False,
                               blockers=['NO11_ACCOUNT_REPORT_WRITE_FAILED'])
        return self.report
