"""R45 exact-source prerequisites and one-shot launch guard. No trading code."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import quote
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
REPOSITORY='Iam-2squared/ark-terminal'
RESEARCH='research/phase57-long-only-cash-equity'
EVIDENCE='docs/evidence/phase57-comprehensive-exit-v1'
PROTOCOL_PATH=EVIDENCE+'/GEN3_PRECOMMIT_R45.json'
PROTOCOL_SHA256='e7b38e7e6aaf909926852467152fffef2532f58f960a95e6f2d18efd66f5d1b5'
LAUNCH_PATH=EVIDENCE+'/GEN3_LAUNCH_R45.json'
CONTRACT_WORKFLOW='.github/workflows/phase57-exit-gen3-contract-r45.yml'
FINITE_WORKFLOW='.github/workflows/phase57-exit-gen3-r45.yml'
R35_RUN=36220335998
R35_ID=10899151845
R35_HASH='a12852e36f270e247a9a0bb7f0f7f618da934297c05f7c687fccb7ceade40434'
CLOSURE_PATH=EVIDENCE+'/GEN3_IMPLEMENTATION_READY_R45.md'
SAFETY_KEYS=frozenset(('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed',
'rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed',
'automaticPromotionAllowed','productionUpdateAllowed','transmitted'))

def require(ok,message):
    if not ok: raise ValueError(message)

def file_sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def _local_module(root: Path, module: str) -> Path | None:
    relative = Path(*module.split("."))
    candidates = [relative.with_suffix(".py"), relative / "__init__.py"]
    # Existing Phase57 scripts support both `scripts.foo` and `foo` imports.
    if not module.startswith("scripts."):
        candidates += [Path("scripts") / item for item in candidates]
    for candidate in candidates:
        if (root / candidate).is_file():
            return candidate
    require(not module.startswith("scripts."), f"missing local dependency: {module}")
    return None


def source_manifest(root: Path) -> dict[str, str]:
    """Hash the full static local import closure, tests, protocol and workflows."""
    seeds = list((root / "scripts").glob("phase57_exit_gen3*_r45.py"))
    seeds += list((root / "scripts").glob("test_phase57_exit_gen3*_r45.py"))
    require(any(path.name == "phase57_exit_gen3_runner_r45.py" for path in seeds),
            "finite runner is absent")
    require(any(path.name.startswith("test_") for path in seeds), "focused tests are absent")
    pending = [path.relative_to(root) for path in seeds]
    included: set[Path] = set()
    while pending:
        relative = pending.pop()
        if relative in included:
            continue
        included.add(relative)
        tree = ast.parse((root / relative).read_text(encoding="utf-8"), str(relative))
        module_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                module_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    parts = list(relative.with_suffix("").parts[:-1])
                    trim = node.level - 1
                    require(trim <= len(parts), f"invalid relative import in {relative}")
                    if trim:
                        parts = parts[:-trim]
                    base = ".".join(parts + ([base] if base else []))
                if base:
                    module_names.add(base)
                    # `from scripts import foo` imports a module, whereas
                    # `from scripts.foo import function` imports an attribute.
                    for alias in node.names:
                        candidate = ".".join((base, alias.name))
                        path = Path(*candidate.split(".")).with_suffix(".py")
                        if (root / path).is_file():
                            module_names.add(candidate)
            elif isinstance(node, ast.Call) and node.args:
                function = node.func
                dynamic = (isinstance(function, ast.Name) and function.id == "__import__") or (
                    isinstance(function, ast.Attribute) and function.attr == "import_module")
                if dynamic:
                    require(isinstance(node.args[0], ast.Constant)
                            and isinstance(node.args[0].value, str),
                            f"unresolved dynamic import in source closure: {relative}")
                    module_names.add(node.args[0].value)
        for module in sorted(module_names):
            local = _local_module(root, module)
            if local is not None and local not in included:
                pending.append(local)
    included.update(map(Path, (PROTOCOL_PATH, CONTRACT_WORKFLOW, FINITE_WORKFLOW, EVIDENCE+"/GEN3_FEATURE_CAUSALITY_AUDIT_R45.json")))
    return {path.as_posix(): file_sha256(root / path) for path in sorted(included)}


def contract_receipt(root):
    path=root/PROTOCOL_PATH
    require(file_sha256(path)==PROTOCOL_SHA256,'R45_PROTOCOL_HASH')
    p=json.loads(path.read_text())
    require(set(p['safety'])==SAFETY_KEYS and all(v is False for v in p['safety'].values()),'R45_SAFETY9')
    require(p['execution']['expectedModelFitCount']==24 and len(p['candidates'])==4,'R45_BUDGET')
    for name,h in {**p['baselineSourceHashes'],**p['reusedGen2SourceHashes']}.items():
        require(file_sha256(root/name)==h,'R45_PINNED_SOURCE:'+name)
    return dict(status='GEN3_PREFLIGHT_CONTRACT_PASS_NOT_PERFORMANCE_PASS',
        executionSha=os.environ.get('ARK_GEN3_EXECUTION_SHA',os.environ.get('GITHUB_SHA')),
        runId=os.environ.get('GITHUB_RUN_ID'),protocolSha256=PROTOCOL_SHA256,
        sourceSha256=source_manifest(root),candidateCount=4,expectedModelFitCount=24,
        modelFits=0,policyReplays=0,performanceInspections=0,providerRequests=0,
        protectedPartitionsOpened=0,safety=p['safety'])


def github_get(path):
    request=Request('https://api.github.com/repos/'+REPOSITORY+path,
                    headers={'Accept':'application/vnd.github+json','User-Agent':'Ark-R45-launch-guard'})
    # Only repository read endpoints are queried. Never log credentials.
    token=os.environ.get('GH_TOKEN')
    if token: request.add_header('Authorization','Bearer '+token)
    with urlopen(request,timeout=30) as response:return json.load(response)


def validate_launch(root,marker,prerequisite,get=github_get):
    current=contract_receipt(root)
    execution=marker['executionSha'];trigger=os.environ['GITHUB_SHA'];runid=int(os.environ['GITHUB_RUN_ID'])
    require(marker['schemaVersion']=='phase57-gen3-launch-r45-v1' and marker['authorizedByUser'] is True,'R45_EXPLICIT_AUTHORIZATION')
    require(os.environ['GITHUB_REPOSITORY']==REPOSITORY and os.environ['GITHUB_RUN_ATTEMPT']=='1','R45_ONE_SHOT_REPOSITORY')
    branch=marker['triggerBranch']
    require(branch.startswith('research/phase57-gen3-r45-launch-') and os.environ['GITHUB_REF']=='refs/heads/'+branch,'R45_TRIGGER_BRANCH')
    require(re.fullmatch('[0-9a-f]{40}',execution) is not None,'R45_EXECUTION_SHA')
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==execution,'R45_CHECKOUT_SHA')
    require(get('/git/ref/heads/'+branch)['object']['sha']==trigger,'R45_LATEST_TRIGGER_HEAD')
    require(get('/git/ref/heads/'+RESEARCH)['object']['sha']==marker['researchHead'],'R45_RESEARCH_HEAD_CHANGED')
    for key in ('protocolSha256','candidateCount','expectedModelFitCount'):
        require(marker[key]==current[key]==prerequisite[key],'R45_CONTRACT_'+key)
    require(prerequisite['sourceSha256']==current['sourceSha256'],'R45_TESTED_SOURCE_MISMATCH')
    require(prerequisite['status']=='GEN3_PREFLIGHT_CONTRACT_PASS_NOT_PERFORMANCE_PASS','R45_CI_RECEIPT')
    require(prerequisite.get('support',{}).get('status')=='GEN3_SUPPORT_AND_INDEPENDENT_LABELS_PASS','R45_SUPPORT_REQUIRED')
    require(prerequisite['support']['independentLabelCheck']['rowsChecked']==656247 and prerequisite['support']['independentLabelCheck']['mismatches']==0,'R45_INDEPENDENT_LABEL_CHECK')
    require(prerequisite['executionSha']==execution==current['executionSha'],'R45_CI_EXECUTION')
    ci=get('/actions/runs/'+str(marker['contractRunId']))
    require(str(marker['contractRunId'])==str(prerequisite['runId']),'R45_CI_RUN_ID')
    require(ci['head_sha']==execution and ci['path']==CONTRACT_WORKFLOW and ci['conclusion']=='success' and ci['status']=='completed','R45_REQUIRED_CI_NOT_PASS')
    for other_sha,allowed in ((marker['researchHead'],{CLOSURE_PATH}), (trigger,{CLOSURE_PATH,LAUNCH_PATH})):
        comparison=get('/compare/'+execution+'...'+other_sha)
        require(comparison['status'] in ('identical','ahead') and comparison['behind_by']==0,'R45_NOT_DESCENDANT')
        files=comparison.get('files',[])
        require(len(files)<300 and {f['filename'] for f in files}<=allowed,'R45_POST_CI_SOURCE_CHANGE')
    current_run=get('/actions/runs/'+str(runid))
    require(current_run['head_sha']==trigger and current_run['path']==FINITE_WORKFLOW,'R45_CURRENT_RUN_IDENTITY')
    # Across all branches, any previous run (even a failure) blocks a silent retry.
    page=1
    while True:
        runs=get('/actions/workflows/'+str(current_run['workflow_id'])+'/runs?per_page=100&page='+str(page))['workflow_runs']
        for row in runs: require(row['id']==runid,'R45_ANOTHER_FINITE_RUN_EXISTS:'+str(row['id']))
        if len(runs)<100:break
        page+=1
    artifact=get('/actions/artifacts/'+str(R35_ID))
    require(artifact['workflow_run']['id']==R35_RUN and artifact['expired'] is False and artifact['digest']=='sha256:'+R35_HASH,'R45_R35_ARTIFACT')
    for status in ('queued','in_progress','waiting','pending'):
        runs=get('/actions/runs?branch='+quote(RESEARCH,safe='')+'&status='+status+'&per_page=100')['workflow_runs']
        require(not any(('gen2-r41.yml' in x.get('path','') or 'finite-r36.yml' in x.get('path','')) for x in runs),'R45_COMPETING_LEARNING')
    return {**current,'status':'GEN3_LAUNCH_VERIFIED','triggerSha':trigger,'triggerBranch':branch,
            'researchHead':marker['researchHead'],'contractRunId':marker['contractRunId'],
            'duplicateFiniteRuns':0,'launchAuthorizedOnlyAfterRequiredCI':True}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=('contract','launch'),required=True)
    parser.add_argument('--marker',type=Path)
    parser.add_argument('--contract-receipt',type=Path)
    parser.add_argument('--support',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    a=parser.parse_args();require(not a.out.exists(),'R45_APPEND_ONLY_OUTPUT')
    a.out.parent.mkdir(parents=True,exist_ok=True)
    if a.mode=='contract':
        require(a.support is not None,'R45_SUPPORT_RECEIPT_REQUIRED')
        receipt=contract_receipt(ROOT)
        support=json.loads(a.support.read_text())
        require(support['status']=='GEN3_SUPPORT_AND_INDEPENDENT_LABELS_PASS' and support['protocolSha256']==PROTOCOL_SHA256,'R45_SUPPORT_IDENTITY')
        receipt['support']=support
    else:
        require(a.marker is not None and a.contract_receipt is not None,'R45_LAUNCH_INPUTS')
        receipt=validate_launch(ROOT,json.loads(a.marker.read_text()),json.loads(a.contract_receipt.read_text()))
    with a.out.open('x') as f:json.dump(receipt,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='sourceSha256'},sort_keys=True))

if __name__=='__main__':main()
