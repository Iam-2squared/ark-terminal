from pathlib import Path
import zipfile,io,hashlib,json,re

root=Path(__file__).resolve().parents[3]
binding=json.loads((root/'repo/docs/evidence/capital-v5-reserve-past-qualified-20261005-v1/INPUT_BINDING.json').read_text())
targets={v['sha256']:k for k,v in binding['roles'].items() if k!='protected100'}
targets['827abcf716c9203a70bc766783948a6be3cee3428abf6a772d1c3495096fd197']='core_runtime'
out=root/'sources/resolved';out.mkdir(parents=True,exist_ok=True)
seen=set();index=[];resolved={};metadata=[]

def walk(source,chain):
    data=source.read_bytes() if isinstance(source,Path) else source
    digest=hashlib.sha256(data).hexdigest()
    if digest in seen:return
    seen.add(digest)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            if info.is_dir():continue
            name=info.filename
            location=chain+'!'+name
            if name.endswith('.zip'):
                walk(z.read(name),location);continue
            if re.search(r'holdout|prospective|protected.*(?:raw|market)|fresh.*(?:raw|market)',name,re.I):
                index.append({'location':location,'bytes':info.file_size,'not_opened':True});continue
            content=z.read(name);h=hashlib.sha256(content).hexdigest()
            index.append({'location':location,'bytes':info.file_size,'sha256':h})
            role=targets.get(h)
            special=any(k in name for k in ['CURRENT_CAUSAL_QUALITY_RUNTIME','CURRENT_MRET_CAP_RUNTIME','CERTIFIED_INDEPENDENT_MRET_OOF_SCORES','FROZEN_MRET_PERCENTILE_TRAIN_SCORES','QUALITY_TRAIN_SCORE_TABLE','CAPITAL_MAX3_SLOT_RESERVE_V1_DECISIONS','CAPITAL_MAX3_SLOT_RESERVE_V1_TRADES','CAPITAL_MAX3_SLOT_RESERVE_V1_RESULT','INDEPENDENT_ACTION_CASES','EXECUTION_SOURCE_COVERAGE'])
            meta=bool(re.search(r'calendar|coverage|session.*receipt|processing.*receipt|source.*manifest|SESSION_SPLIT|MANIFEST|COMPLETE|prepare\.py',name,re.I)) and info.file_size<300000
            if role or special or meta:
                path=out/(role or h[:12]+'_'+Path(name).name)
                if not path.exists():path.write_bytes(content)
                obj={'local_path':str(path),'sha256':h,'bytes':len(content),'archive_member':location}
                if role:resolved[role]=obj
                if special or meta:metadata.append(obj)

import sys
for name in sys.argv[1:]:
    source=Path(name).resolve();walk(source,source.name)
(out/'RESOLVED_INPUTS.json').write_text(json.dumps({'resolved':resolved,'metadata':metadata,'unique_archives':len(seen)},indent=2)+'\n')
(out/'ARCHIVE_MEMBER_INDEX.json').write_text(json.dumps(index,indent=2)+'\n')
print(json.dumps({'unique_archives':len(seen),'member_N':len(index),'resolved_roles':list(resolved),'missing_roles':[v for h,v in targets.items() if v not in resolved],'metadata_paths':[x['local_path'] for x in metadata]},indent=2))
