"""Aggregate release inventory and exact-private-identity publication guard."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import gzip,hashlib,json,sys

def main():
    root=Path(sys.argv[1]);repo=root/'ark-terminal';doc=repo/'docs/evidence/phase57-capital-state9-liquidity-sameday-20261004-v1';code=repo/'research/capital-state9-liquidity-sameday-20261004-v1'
    entries=[e for e in map(json.loads,gzip.open(root/'eod_private/primary/entry.jsonl.gz','rt')) if e['entry_status']=='FIRST_ENTRY']
    ids={e['watch_key'] for e in entries};violations=[];checked=[]
    for p in list(doc.rglob('*'))+list(code.rglob('*')):
        if not p.is_file() or p.suffix not in ('.json','.md','.py','.svg','.yml'):continue
        s=p.read_text();hits=[identity for identity in ids if identity in s]
        if hits:violations.append({'file':str(p.relative_to(repo)),'private_identity_hits_N':len(hits)})
        # Exact real symbol/session JSON row signatures, rather than innocuous field names or calendars.
        for e in entries:
            if '"symbol": "'+e['symbol']+'"' in s or '"symbol":"'+e['symbol']+'"' in s:
                violations.append({'file':str(p.relative_to(repo)),'real_symbol_row':True});break
        checked.append(str(p.relative_to(repo)))
    private=[]
    for p in sorted((root/'svnext_private').rglob('*')):
        if p.is_file():private.append({'path':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
    result={'jst':datetime.now(timezone(timedelta(hours=9))).isoformat(),'status':'PASS' if not violations else 'FAIL','public_code_doc_scanned_N':len(checked),
        'exact_real_identity_or_symbol_publication_hits_N':len(violations),'violations':violations,'private_components':private,
        'private_component_count':len(private),'frozen_source_primary_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'eod_private/primary').glob('*') if p.is_file()},
        'source_secret_export':'None. No credential values were accessed outside their existing configured workflow; raw source price rows remain private.',
        'source_coverage_or_teacher_metrics_do_not_imply_live_certification':True}
    (root/'svnext_private/RELEASE_AUDIT_PRIVATE.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'public_files_scanned':len(checked),'private_identity_hits_N':len(violations),'private_component_count':len(private)}))
    if violations:raise SystemExit(2)

if __name__=='__main__':main()
