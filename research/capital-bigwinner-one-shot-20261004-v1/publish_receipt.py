"""Sync identical public tree and write an actual post-publication receipt."""
import subprocess
import sys
from checkpoint import ROOT, OUT, git, save, now, sha

label,parent,result,tree=sys.argv[1:5]
subprocess.run(['git','fetch','origin','refs/heads/capital-state9-vnext-20261004'],cwd=ROOT,check=True)
assert git('rev-parse','FETCH_HEAD')==result
assert git('write-tree')==tree,'LOCAL_REMOTE_TREE_MISMATCH'
assert git('rev-parse','HEAD')==parent
subprocess.run(['git','reset','--soft',result],cwd=ROOT,check=True)
save(OUT/'receipts'/f'{label}.json',{'jst':now(),'basis_head':parent,
    'result_head':result,'remote_confirmed_head':result,'tree_sha':tree,
    'receipt_written_after_commit':True,'force_push':0,'main_merge':0})
print('REMOTE_CHECKPOINT_CONFIRMED',label,result)
