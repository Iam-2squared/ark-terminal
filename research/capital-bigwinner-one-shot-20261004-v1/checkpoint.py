"""Append-only research checkpoints; receipts are written only after commit/push."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
NAME = 'capital-bigwinner-one-shot-20261004-v1'
OUT = ROOT / 'docs/evidence' / NAME
SAFETY = {k: False for k in ('executionAllowed','brokerWriteAllowed',
    'excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed',
    'paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed',
    'transmitted','productionReady')}

def now():
    return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()

def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:
        json.dump(value,f,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)
        f.write('\n')

def checkpoint(label, status, results, blockers, next_direction, extras=()):
    basis = git('rev-parse','HEAD')
    assert git('branch','--show-current') == 'capital-state9-vnext-20261004'
    hashes = {}
    for n in ('DESIGN_PRECOMMIT.json','FEATURE_LIQUIDITY_MANIFEST.json','MODEL_PRECOMMIT.json'):
        p = OUT/n
        hashes[n] = sha(p) if p.exists() else None
    private = ROOT.parent/'bigwinner_private'
    source = private/'SOURCE_MANIFEST_RECOVERED.json'
    if not source.exists():source = private/'SOURCE_MANIFEST.json'
    record = {'jst':now(),'repo':'Iam-2squared/ark-terminal',
        'branch':git('branch','--show-current'),'basis_head':basis,
        'result_head_receipt':f'receipts/{label}.json',
        'source_hashes':json.loads(source.read_text()) if source.exists() else {},
        'config_hash':hashes['DESIGN_PRECOMMIT.json'],
        'feature_manifest_hash':hashes['FEATURE_LIQUIDITY_MANIFEST.json'],
        'model_precommit_hash':hashes['MODEL_PRECOMMIT.json'],
        'model_hash':sha(private/'MODEL_HASHES.json') if (private/'MODEL_HASHES.json').exists() else None,
        'safety':SAFETY,'orders':0,'current_state':status,
        'results':results,'blockers':blockers,'next_direction':next_direction}
    checkpoint_path = OUT/'checkpoints'/f'{label}.json'
    if checkpoint_path.exists():
        assert not git('ls-files',str(checkpoint_path.relative_to(ROOT))), 'CHECKPOINT_ALREADY_COMMITTED'
        existing = json.loads(checkpoint_path.read_text())
        assert existing['basis_head'] == basis and existing['current_state'] == status
    else:
        save(checkpoint_path,record)
    paths = [str(OUT.relative_to(ROOT)),str(Path(__file__).parent.relative_to(ROOT)),*extras]
    subprocess.run(['git','add','--sparse','--',*paths],cwd=ROOT,check=True)
    if not git('config','user.name'):
        raise RuntimeError('Git author not configured')
    print(json.dumps({'checkpoint':label,'basis_head':basis,'status':status,
        'message':f'Capital BigWinner {label}: {status}'}))

if __name__ == '__main__':
    v=json.loads(Path(sys.argv[1]).read_text())
    checkpoint(**v)
