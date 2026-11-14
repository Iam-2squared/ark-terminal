"""Checkpoint metadata only. Never imports labels, models, or policy runners."""
import datetime
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DOCUMENT_ID = 'WORK_STATE9_SAFE_UPSIDE_HYBRID_ENTRY_20261003_V1'
SAFETY = {k: False for k in ('executionAllowed', 'brokerWriteAllowed',
    'excelOrderWriteAllowed', 'rssOrderFunctionAllowed', 'liveTradingAllowed',
    'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed',
    'transmitted')}

def write(name, value):
    p = ROOT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def prepare(config):
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
    cp = dict(config)
    cp.update(document_id=DOCUMENT_ID, saved_at_jst=now, safety=SAFETY,
        productionReady=False, instrument_scope='LONG_ONLY_CASH_EQUITY')
    write('CHECKPOINTS/' + cp['checkpoint'] + '.json', cp)
    lines = ['# 💾 ' + cp['checkpoint'], '']
    for key in ('saved_at_jst', 'basis_head', 'previous_checkpoint_result_head',
                'current_status', 'completed_this_checkpoint', 'key_evidence',
                'blockers', 'current_direction', 'next_step', 'frozen_boundaries',
                'exposure_and_budget'):
        value = cp.get(key)
        lines += ['## 📌 ' + key, '', json.dumps(value, ensure_ascii=False, indent=2), '']
    lines += ['Result HEADは保存後のGitHub commitが正本。未来のSHAは本文に記録しない。', '']
    (ROOT / 'CHECKPOINTS' / (cp['checkpoint'] + '.md')).write_text('\n'.join(lines))
    files = []
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.name != 'MANIFEST.json':
            b = p.read_bytes()
            files.append(dict(path=str(p.relative_to(ROOT)), bytes=len(b),
                sha256=hashlib.sha256(b).hexdigest(),
                git_blob_sha=hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()))
    write('MANIFEST.json', dict(document_id=DOCUMENT_ID, generated_at_jst=now,
        basis_head=cp['basis_head'], current_status=cp['current_status'], files=files,
        self_excluded=True, safety=SAFETY))
    return cp

if __name__ == '__main__':
    cp = prepare(json.loads(sys.argv[1]))
    metadata_only = len(sys.argv) > 2 and sys.argv[2] == '--metadata-only'
    repo = ROOT.parents[1]
    out = []
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            b = p.read_bytes()
            item = dict(path=str(p.relative_to(repo)), bytes=len(b), sha256=hashlib.sha256(b).hexdigest())
            if len(b) > 10000 or p.suffix in ('.gz', '.png', '.zip', '.npy'):
                item['binary'] = True
            elif not metadata_only:
                item['content'] = b.decode()
            out.append(item)
    for name in cp.get('extra_paths', []):
        p = repo / name
        b = p.read_bytes()
        item = dict(path=name, bytes=len(b), sha256=hashlib.sha256(b).hexdigest())
        if not metadata_only:
            item['content'] = b.decode()
        out.append(item)
    print(json.dumps(dict(checkpoint=cp, files=out), ensure_ascii=False))
