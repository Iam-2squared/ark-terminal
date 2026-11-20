"""Fast-forward checkpoint using a private temporary index, never the user index.

The caller must GET actual GitHub HEAD immediately before invoking and verify
the result with another read-only GET. Git transport supports the 20MB label
whose base64 exceeds the connector request-body limit. No force push.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from evidence_checkpoint import prepare

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
BRANCH='state9-safe-upside-hybrid-entry-20261003-v1'
def run(args,env=None,input=None):
    return subprocess.check_output(['git']+args,cwd=REPO,env=env,input=input,text=True).strip()
def publish(cfg):
    raise RuntimeError('Disabled after safety review: never publish the entire directory. Public checkpoint uses an explicit metadata/aggregate/source allowlist; row-level price data remains private pending explicit publication authority.')
    assert cfg['basis_head']==cfg['previous_checkpoint_result_head']
    basis=cfg['basis_head'];assert run(['cat-file','-t',basis])=='commit'
    cp=prepare(cfg)
    with tempfile.TemporaryDirectory(prefix='entry-checkpoint-index-') as temporary:
        env=dict(os.environ,GIT_INDEX_FILE=str(Path(temporary)/'index'))
        run(['read-tree',basis],env=env)
        files=[p for p in sorted(ROOT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
        for p in files:
            blob=run(['hash-object','-w',str(p)])
            run(['update-index','--add','--cacheinfo','100644',blob,str(p.relative_to(REPO))],env=env)
        tree=run(['write-tree'],env=env)
        message='State9 Safe-Upside '+cp['checkpoint']+': '+cp['current_status']+' [skip ci]\n'
        commit=run(['-c','user.name=Codex','-c','user.email=codex@openai.com','commit-tree',tree,'-p',basis],input=message)
        # The normal non-force refspec rejects a concurrently changed branch.
        run(['push','origin',commit+':refs/heads/'+BRANCH])
    print(json.dumps(dict(checkpoint=cp['checkpoint'],basis_head=basis,result_head=commit,
        saved_at_jst=cp['saved_at_jst'],files=len(files),force=False,user_index_changed=False,
        post_get='REQUIRED_BY_CALLER')))
if __name__=='__main__':publish(json.loads(sys.argv[1]))
