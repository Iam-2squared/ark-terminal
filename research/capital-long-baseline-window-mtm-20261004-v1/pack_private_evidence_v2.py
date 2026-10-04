"""Package private known-prefix Evidence; never fabricate full portfolio metrics."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import argparse,gzip,hashlib,json,zipfile

def digest(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('root',type=Path);parser.add_argument('closure_head');parser.add_argument('packaging_head')
    args=parser.parse_args();root=args.root.resolve()
    private=root/'long_mtm_private'
    docs=root/'ark-terminal/docs/evidence/phase57-capital-long-baseline-window-mtm-20261004-v1'
    closure=json.loads((docs/'CAPITAL_BASELINE_CLOSURE.json').read_text())
    if closure['full_portfolio_measurement']!='BLOCKED':raise RuntimeError('WRONG_PACKAGE_SCOPE')
    members={p.name:p.read_bytes() for p in sorted(private.iterdir()) if p.is_file() and p.suffix in ('.json','.gz')}
    counts={}
    for name in ['CAPITAL_DECISIONS.jsonl.gz','PORTFOLIO_CURVES.jsonl.gz','TRADES_PRIVATE.jsonl.gz','INDEPENDENT_FRAMES_PRIVATE.jsonl.gz']:
        counts[name]=len(gzip.decompress(members[name]).splitlines())
    if counts!={'CAPITAL_DECISIONS.jsonl.gz':9600,'PORTFOLIO_CURVES.jsonl.gz':108,'TRADES_PRIVATE.jsonl.gz':12,'INDEPENDENT_FRAMES_PRIVATE.jsonl.gz':6}:
        raise RuntimeError('KNOWN_PREFIX_COUNTS_MISMATCH')
    independent_frame_N=sum(len(json.loads(line)['frames']) for line in gzip.decompress(members['INDEPENDENT_FRAMES_PRIVATE.jsonl.gz']).splitlines())
    if independent_frame_N!=108:raise RuntimeError('NESTED_INDEPENDENT_FRAME_COUNT_MISMATCH')
    if json.loads(members['INDEPENDENT_MISMATCHES_PRIVATE.json']):raise RuntimeError('AUDIT_MISMATCH')
    readme="""# Private Evidence — current LONG-only baseline\n\nFull portfolio measurement is BLOCKED by an empty funded5m MTM source window.\nThis is not an old historical Capital result and contains no State9-aware new Capital evaluation.\nCAPITAL_DECISIONS includes operational cutoff flags and NOT_EVALUATED_AFTER_MEASUREMENT_BLOCKED; no full funding trace claim.\nPORTFOLIO_CURVES and INDEPENDENT_FRAMES contain known prefix only, not full equity curves.\nTRADES contains two closed trades per arm; no full daily/rolling20 result is provided.\nFUNDED_BLOCKERS is private row-level and must not be pushed to a public repository.\nReproduction code and contracts are pinned to the public closure commit in PACKAGE_MANIFEST.\nParent source hashes are references only; this pack does not re-download or alter the frozen inputs.\n"""
    members['README_PRIVATE.md']=readme.encode()
    manifest={
      'jst':datetime.now(timezone(timedelta(hours=9))).isoformat(),
      'repo':'Iam-2squared/ark-terminal','branch':'capital-state9-vnext-20261004',
      'closure_commit':args.closure_head,'packaging_implementation_commit':args.packaging_head,'status':closure['status'],
      'public_evidence_directory':'docs/evidence/phase57-capital-long-baseline-window-mtm-20261004-v1',
      'private_row_level':True,'full_portfolio_measurement':False,
      'curve_role':'KNOWN_PREFIX_ONLY_NOT_FULL_PORTFOLIO','record_counts':counts,'nested_independent_frames_N':independent_frame_N,
      'source_hashes':closure['source_hashes'],
      'immutable_parent_package':{
        'filename':'Ark_Capital_vNext_Closure_20261004_PRIVATE.zip',
        'sha256':'ef0bc262f92c8c7d7afb4af4c2f9ec3c3504c844775d46cc99881222be4169f7',
        'bytes':22883763},
      'members':[{'path':name,'bytes':len(data),'sha256':digest(data)} for name,data in sorted(members.items())],
      'budgets':closure['budgets'],'safety':closure['safety']}
    members['PACKAGE_MANIFEST.json']=canonical(manifest)
    destination=root/'deliverables/capital-long-baseline-window-mtm-20261004-v1'
    destination.mkdir(parents=True,exist_ok=True)
    target=destination/'Ark_LONG_Capital_Baseline_Window_MTM_20261004_PRIVATE.zip'
    if target.exists():raise FileExistsError('Append-only pack identity already exists')
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(members.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,4,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100600<<16
            z.writestr(info,data)
    with zipfile.ZipFile(target) as z:
        if z.testzip() is not None:raise RuntimeError('ZIP_CRC_FAILED')
        for name,data in members.items():
            if digest(z.read(name))!=digest(data):raise RuntimeError('ZIP_MEMBER_HASH_FAILED')
    print(json.dumps({'local_path':str(target),'sha256':digest(target.read_bytes()),'bytes':target.stat().st_size,
                      'member_N':len(members),'record_counts':counts,
                      'closure_commit':args.closure_head,'verification':'PASS'},indent=2))

if __name__=='__main__':main()
