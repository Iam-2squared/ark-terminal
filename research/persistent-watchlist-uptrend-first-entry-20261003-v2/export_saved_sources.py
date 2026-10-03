"""Copy only already-saved Development inputs. No provider, fit or policy run."""
import gzip,hashlib,json,os
from pathlib import Path
ROOT=Path.cwd()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def save(p,x):
 b=(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
 p.write_bytes(gzip.compress(b,mtime=0))
out=Path(os.environ['RUNNER_TEMP'])/'persistent-saved-source';out.mkdir()
sub=ROOT/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate'
rawpath=sub/'raw-paths-evaluator-only.json.gz'
assert sha(rawpath)=='37853e73799544be6fd6eb955de514073dd13671692426291a9fdb6d80056c6b'
r1=next((Path(os.environ['RUNNER_TEMP'])/'saved-R1').rglob('prefit/rows.json'))
rows=load(r1)
assert sha(r1)=='54f7dbb8bd0c9f8974ccccb7a949c0b7ebf0bbe46581be7778f1607f9d9d8cb6'
ids={r['opportunity'] for r in rows};assert len(ids)==4931
split=load(ROOT/'docs/evidence/phase57-behavior-expansion-v1/04_session_split_manifest.json')
allow=set(split['intradayDevelopment']);blocked=set(split['commonHoldout'])|set(split['excluded'])
assert not allow & blocked
assert all(r['session'] in allow and r['session'] not in blocked for r in rows)
raw=load(rawpath);selected={k:raw[k] for k in sorted(ids)}
assert all(k.split('|')[0] in allow and v['previousSession'] is None or v['previousSession'] in allow for k,v in selected.items())
save(out/'raw_paths_selected.json.gz',selected)
opps=load(sub/'opportunities.json.gz');save(out/'substrate_opportunities.json.gz',[x for x in opps if x['id'] in ids])
parents={'raw_paths_original':{'path':str(rawpath.relative_to(ROOT)),'sha256':sha(rawpath)},'r1_rows':{'sha256':sha(r1)}}
for name,path in {
 'canonical_opportunities.json.gz':'docs/evidence/phase57-entry-timing-signal-census-v1/measurement/opportunity-records.json.gz',
 'geometry_rows.jsonl.gz':'research/entry-geometry-capture-baseline-20261002/GEOMETRY_ROWS.jsonl.gz',
 'selector_events_original.ndjson.gz':'docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz',
 'source_ledger.json':'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/source-ledger.json',
 'split_original.json':'docs/evidence/phase57-behavior-expansion-v1/04_session_split_manifest.json'
}.items():
 p=ROOT/path;assert p.is_file();(out/name).write_bytes(p.read_bytes());parents[name]={'path':path,'sha256':sha(p),'bytes':p.stat().st_size}
receipt={'status':'SAVED_DEVELOPMENT_SOURCE_EXPORT_COMPLETE','basis_head':os.environ['GITHUB_SHA'],
 'selected_watches':len(ids),'sessions':len({r['session'] for r in rows}),'parents':parents,
 'files':{p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.iterdir())},
 'provider_requests':0,'model_fits':0,'teacher_computations':0,'policy_runs':0,'protected_opens':0,
 'previous_source_proof':'research/state9-safe-upside-hybrid-entry-20261003/ORIGINAL_SAVED_SOURCE_PROOF.json',
 'known_at':'UNKNOWN; bar end research assumption','new_data_acquisition':False}
(out/'SOURCE_EXPORT_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k not in ['parents','files']}))
