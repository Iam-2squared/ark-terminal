"""Whole-tree allowed-path comparison and exact V1/frozen byte protections."""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import subprocess
import sys

V2="research/preopen-selector-v2-20261014/"
WORKFLOW=".github/workflows/preopen-selector-v2-synthetic.yml"


def audit_repo(repo: Path, base: str) -> dict:
    def git(*args):return subprocess.check_output(["git","-C",str(repo),*args],text=True).strip()
    baseline=json.loads((repo/V2/"PROTECTED_SURFACE_BASELINE.json").read_text())
    if base!=baseline["base_head"]:
        raise ValueError("PROTECTED_BASE_REF_DRIFT")
    changed=set(git("diff","--name-only",base).splitlines())
    changed.update(git("ls-files","--others","--exclude-standard").splitlines())
    if any(not p.startswith(V2) and p!=WORKFLOW for p in changed):
        raise ValueError("WRITE_OUTSIDE_V2_ALLOWED_SURFACES")
    protected=[]
    for line in git("ls-tree","-r","HEAD").splitlines():
        p=line.split("\t")[1]
        if not p.startswith(V2) and p!=WORKFLOW:protected.append(line)
    if hashlib.sha256(("\n".join(protected)+"\n").encode()).hexdigest()!=baseline["protected_git_tree_entry_sha256"]:
        raise ValueError("PROTECTED_TREE_DRIFT")
    v1=repo/"research/independent-long-selector-20261012-v1"
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(v1.glob("*.py"))}
    if files!=baseline["v1_root_python_files"]:
        raise ValueError("V1_ROOT_PYTHON_CHANGED_OR_ADDED")
    old=repo/V2/"V2_DESIGN-ja.md"
    history=repo/V2/"history/V2_DESIGN_INITIAL_4b02c4eb-ja.md"
    if old.read_bytes()!=history.read_bytes() or hashlib.sha256(old.read_bytes()).hexdigest()!=baseline["old_design_sha256"]:
        raise ValueError("INITIAL_V2_DESIGN_BYTE_DRIFT")
    forbidden={".joblib",".pickle",".pkl",".sqlite",".db",".zip",".gguf"}
    paths=[repo/p for p in changed if (repo/p).is_file()]
    if any(p.suffix in forbidden for p in paths):
        raise ValueError("PRIVATE_OR_MODEL_ARTIFACT_IN_PUBLIC_DIFF")
    return {"status":"PASS","allowed_changed_files":len(changed),"v1_protected_code_hash":baseline["v1_computation_sha256"],"protected_tree_unchanged":True,"initial_design_byte_identical":True}


if __name__=="__main__":
    root=Path(__file__).resolve().parents[3]
    print(json.dumps(audit_repo(root,sys.argv[1] if len(sys.argv)>1 else "4b02c4eb6fed0b75bfc7a6e8afc49d7868696159"),sort_keys=True))
