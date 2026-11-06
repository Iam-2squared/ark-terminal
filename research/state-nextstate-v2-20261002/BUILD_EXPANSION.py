from pathlib import Path
import shutil,json,hashlib,zipfile,base64,ast,fnmatch
R=Path(__file__).resolve().parent;W=R.parent;V=W/'state_predictiveness_20261002_v1';T=R/'runner';T.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for n in ['input_gate.py','normalize80.py','normalize120.py','PATH_FROZEN.py','CAUSAL_FEATURE_BUILDER.py','profile.json','source_snapshot.json','engine_stream.py']:
 shutil.copyfile(V/'runner'/n,T/n)
shutil.copytree(V/'runner/candidate',T/'candidate',dirs_exist_ok=True)
for n in ['FEATURE_SCHEMA_V2.json','PREDICTIVENESS_V2_CONTRACT.md','PREDICTIVENESS_V2_PRECOMMIT.json','DATA_SCOPE_V2.json','BUDGET_START_V2.json']:shutil.copyfile(R/n,T/n)
shutil.copyfile(R/'runner_config.json',T/'config.json')
src=(W/'state9_rc2_market_audit/continuity_20261001_200641/runner/run.py').read_text().split("status='ACQUIRING_G1_INPUTS'")[0]
src=src.replace('from scripts import phase57_expansion_data as existing','class NoRedirect(urllib.request.HTTPRedirectHandler):\n def redirect_request(self,*args,**kwargs):return None')
src=src.replace('existing.NoRedirect()','NoRedirect()').replace("time.sleep(2.6);requests+=1","time.sleep(1.1);requests+=1\n  assert requests<=CFG['maxrequests'],'PROVIDER_REQUEST_CAP'")
(T/'acquisition_base.py').write_text(src)
code='''from pathlib import Path
import os,json,hashlib,shutil,subprocess,traceback,sys
from fractions import Fraction
import acquisition_base as a
from input_gate import map_rows,scheduled_minutes
import normalize80,normalize120
from PATH_FROZEN import PathBuilder
from CAUSAL_FEATURE_BUILDER import FeatureBuilder
H=Path(__file__).resolve().parent;OUT=a.OUT;RAW=a.RAW;cfg=a.CFG
schema=json.loads((H/'FEATURE_SCHEMA_V2.json').read_text());steps=0;completed=0;children=[];status='NOT_STARTED';error=None;proposals=[];skips=[];datasets=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):a.write(OUT/n,x)
try:
 pre=json.loads((H/'PREDICTIVENESS_V2_PRECOMMIT.json').read_text())
 for n,v in pre['hashes'].items():
  if (H/n).exists():assert sha(H/n)==v,'V2_PRECOMMIT_CHANGED'
 ss=json.loads((H/'source_snapshot.json').read_text())
 for n in ['candidate/api.py','candidate/exact.py','candidate/kernel.py','profile.json']:assert sha(H/n)==ss[n],'FROZEN_IDENTITY'
 assert bool(os.environ.get('JQUANTS_API_KEY')),'BINDING_UNAVAILABLE'
 exc={(r['date'],r['code']) for r in cfg['exclusion_pairs']};cache={}
 for link in cfg['acquisition_session_scope']:
  d,p=link['date'],link['previous']
  for day in [d,p]:
   if day not in cache:cache[day]=a.fetch(day,'master')
  cur={r['Code']:r for r in cache[d] if isinstance(r.get('Code'),str)};old={r['Code']:r for r in cache[p] if isinstance(r.get('Code'),str)}
  pool=[]
  for c,r in cur.items():
   if c not in old or not a.compatible(r,old[c]) or (d,c) in exc or (p,c) in exc:continue
   mh=hashlib.sha256(json.dumps({k:v for k,v in r.items() if k!='_source'},sort_keys=True,separators=(',',':')).encode()).hexdigest();pool.append((mh,c,r))
  proposed=0
  for mh,c,r in sorted(pool):
   if proposed==3:break
   fac=a.fetch(d,'daily',c)+a.fetch(p,'daily',c)
   if len(fac)!=2 or any('ExRT' not in f or not isinstance(f.get('AdjFactor'),a.Token) or f['ExRT'] is not None or a.Decimal(f['AdjFactor'])!=1 for f in fac):skips.append({'date':d,'code':c,'reason':'ACTION_UNAVAILABLE'});continue
   proposals.append({'date':d,'previous':p,'code':c,'market':r['Mkt'],'security_id':r['Mkt']+'|'+c,'session_id':'JPX:'+d,'previous_session_id':'JPX:'+p,'audit_key':d+'|'+r['Mkt']+'|'+c,'master_current_source':r['_source'],'master_previous_source':old[c]['_source'],'factor_sources':[f['_source'] for f in fac],'acquisition_metadata_hash':mh,'raw_basis':'UNADJUSTED','unit':'JPY'});proposed+=1
 assert len(proposals)<=72,'PROPOSAL_CAP'
 save('ACQUISITION_UNIVERSE_PRECOMMIT.json',{'at':a.now(),'proposals':proposals,'price_rows_read':0,'State_results_used':False,'after_price_refill':False})
 for k,pair in enumerate(proposals,1):
  d,p,c=pair['date'],pair['previous'],pair['code'];cur=a.fetch(d,'minute',c);prev=a.fetch(p,'minute',c)
  good,why=a.good(cur);goodp,whyp=a.good(prev)
  if not good or not goodp or a.adjacency(prev)==0:skips.append({'date':d,'code':c,'reason':why or whyp or 'NO_PREVIOUS_ADJACENT_RETURNS'});continue
  mapped=map_rows(cur);norm=normalize80.generate(prev,mapped);ref=normalize120.regenerate(prev,mapped)
  assert all(norm[x]==ref[x] for x in ['U','P_ref','coordinates','previous_return_pairs_N','previous_pair_ids']),'M0_80_120_MISMATCH'
  pid=f'N{k:03d}';look={m['t']:(m,x) for m,x in zip(mapped,norm['coordinates'])};schedule=scheduled_minutes(d);trade=[m for m in schedule if m not in (691,931 if d>='2024-11-05' else 901)];ti={m-540:i for i,m in enumerate(trade)}
  sandbox=RAW/'workers'/pid;sandbox.mkdir(parents=True)
  shutil.copytree(H/'candidate',sandbox/'candidate');shutil.copyfile(H/'profile.json',sandbox/'profile.json');shutil.copyfile(H/'engine_stream.py',sandbox/'engine_stream.py')
  child=subprocess.Popen([sys.executable,'engine_stream.py'],cwd=sandbox,env={'PATH':os.environ['PATH'],'LANG':'C.UTF-8','PYTHONHASHSEED':'0','PYTHONIOENCODING':'utf-8'},stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1);children.append(child)
  path=PathBuilder(pid);fb=FeatureBuilder(schema);ft=OUT/'FEATURES'/f'{pid}.jsonl';st=OUT/'STATE9_TRACES'/f'{pid}.jsonl';ep=OUT/'PATH_ENDPOINTS'/f'{pid}.jsonl'
  for f in [ft,st,ep]:f.parent.mkdir(parents=True,exist_ok=True)
  observed=0
  with ft.open('w') as f,st.open('w') as s,ep.open('w') as e:
   for m in schedule:
    t=m-540;found=look.get(t);raw=None if found is None else {'t':t,'known_at':t,'source':found[0]['source'],'auction':found[0]['auction'],**{x.lower():found[1][x] for x in ['O','H','L','C']}}
    steps+=1;assert steps<=36864,'KERNEL_CAP';child.stdin.write(json.dumps({'t':t,'raw':raw,'case_id':pid})+'\\n');child.stdin.flush();line=child.stdout.readline();assert line,'WORKER_STOP';state=json.loads(line)
    assert state['as_of']==t and (state['observed_at'] is None or state['observed_at']<=t),'STATE_FUTURE'
    if raw is not None and state['numeric_status']=='ACCEPTED':assert Fraction(state['close_u'])==Fraction(raw['c']),'CLOSE_MAPPING'
    end=d+'T'+f'{m//60:02d}:{m%60:02d}:00+09:00';slot={'scheduled_t':t,'bar_end':end,'row_status':'OBSERVED' if found else 'UNKNOWN_GAP'};before=len(path.events);endpoint=path.push(state,slot);events=path.events[before:];features=fb.push(state,endpoint,events,path.runs);observed+=int(state['current_semantics_observed'])
    row={'row_key':pair['security_id']+'|'+pair['session_id']+'|'+end,'pair_id':pid,'security_id':pair['security_id'],'session_id':pair['session_id'],'date':d,'bar_end':end,'scheduled_t':t,'tradable_index':ti.get(t),'causal_segment_id':endpoint['causal_segment_id'],'run_id':endpoint['run_id'],'source_pointer':None if found is None else found[0]['_source'],'feature_max_timestamp':end,'feature_created_before_target':True,'features':features,'audit_source':{'Close_JPY':None if found is None else found[0]['C'],'x_C':None if found is None else found[1]['C'],'U':norm['U'],'numeric_status':state['numeric_status'],'raw_present':found is not None,'auction':None if found is None else found[0]['auction'],'source':None if found is None else found[0]['source'],'observed':state['current_semantics_observed'],'formal_primary':endpoint['Primary_or_null'],'local_direction':state['leg_direction'],'events':[{x:v[x] for x in ['event_type','scheduled_t','bar_end','causal_segment_id','from_primary_or_null','to_primary_or_null']} for v in events]}}
    for writer,obj in [(f,row),(s,state),(e,endpoint)]:writer.write(json.dumps(obj,sort_keys=True,separators=(',',':'))+'\\n')
  child.stdin.close();assert child.wait(timeout=30)==0,'WORKER_FAILURE';completed+=1
  datasets.append({**pair,'pair_id':pid,'scheduled_endpoints_N':len(schedule),'raw_current_N':len(mapped),'raw_previous_N':len(prev),'observed_semantic_N':observed,'formal_null_N':len(schedule)-observed,'feature_SHA256':sha(ft),'state_trace_SHA256':sha(st),'path_endpoint_SHA256':sha(ep),'U':norm['U'],'price_basis':'UNADJUSTED_JPY','source_identity':hashlib.sha256(json.dumps([r['_source'] for r in cur+prev],sort_keys=True).encode()).hexdigest(),'trace_mode':'FROZEN_CURRENT_SLOT_GENERATION'})
  save('M0_RECEIPTS/'+pid+'.json',{'U':norm['U'],'P_ref':norm['P_ref'],'previous':p,'precision80_120_match':True,'previous_return_pairs_N':norm['previous_return_pairs_N'],'previous_pair_ids':norm['previous_pair_ids']})
  save('DATASET_MANIFEST.json',{'pairs':datasets,'features_completed_before_label_builder':True,'endpoint_N':sum(p['scheduled_endpoints_N'] for p in datasets),'new_kernel_steps':steps,'new_provider_requests':a.requests})
  print(json.dumps({'pairs_completed':completed,'new_steps':steps,'provider_requests':a.requests,'labels_created':0}),flush=True)
 status='EXPANSION_FEATURES_READY'
except Exception as ex:
 code=str(ex);error={'type':type(ex).__name__,'code':code if code and all(c.isupper() or c.isdigit() or c=='_' for c in code) else 'SANITIZED_TECHNICAL_EXCEPTION','locations':[{'file':Path(f.filename).name,'line':f.lineno} for f in traceback.extract_tb(ex.__traceback__)]};status='EXPANSION_FAILED_LOCAL_CORPUS_REMAINS'
finally:
 for child in children:
  if child.poll() is None:child.terminate();child.wait(timeout=30)
 save('SOURCE_RECEIPTS.json',a.receipts);save('SKIPS.json',skips)
 save('RUNNER_FINAL_RECEIPT.json',{'status':status,'error':error,'provider_requests':a.requests,'new_steps':steps,'completed_pairs':completed,'proposals':len(proposals),'future_classifier_input':0,'secret_values_exported':0,'raw_pages_exported':0,'protected_requests':0,'old16FAIL':16,'old88incident':88})
 assert RAW.name=='state-nextstate-v2-raw' and RAW.parent==Path(os.environ['RUNNER_TEMP']),'PURGE_BOUNDARY'
 shutil.rmtree(RAW);save('PURGE_RECEIPT.json',{'verified':not RAW.exists(),'raw_pages_exported':0})
 save('MANIFEST.json',{'files':[{'path':str(p.relative_to(OUT)),'SHA256':sha(p),'bytes':p.stat().st_size} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='MANIFEST.json']})
 print(json.dumps({'status':status,'error':error,'purged':not RAW.exists(),'provider_requests':a.requests,'new_steps':steps}),flush=True)
if error:sys.exit(1)
'''
(T/'export_expansion.py').write_text(code)
for p in T.glob('*.py'):ast.parse(p.read_text())
payload=R/'EXPANSION_PAYLOAD.zip'
with zipfile.ZipFile(payload,'x',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(T.rglob('*')):
  if p.is_file() and '__pycache__' not in str(p):z.write(p,str(p.relative_to(T)))
(R/'EXPANSION_PAYLOAD.b64').write_text(base64.b64encode(payload.read_bytes()).decode()+'\n')
workflow='''name: State NextState V2 Development Export
on:
  push:
    branches: [state-predictiveness-v2-nextstate-20261002-v1]
    paths: ['.github/workflows/state-nextstate-v2-20261002.yml', 'research/state-nextstate-v2-20261002/payload.b64']
permissions:
  contents: read
concurrency:
  group: state-nextstate-v2-20261002
  cancel-in-progress: false
jobs:
  development-export:
    if: github.ref == 'refs/heads/state-predictiveness-v2-nextstate-20261002-v1'
    runs-on: ubuntu-latest
    timeout-minutes: 35
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      - name: Verify source package
        run: |
          python - <<'PY'
          import pathlib,os,zipfile,base64,io,hashlib
          b=base64.b64decode(pathlib.Path('research/state-nextstate-v2-20261002/payload.b64').read_bytes())
          assert hashlib.sha256(b).hexdigest()=='PAYLOAD_HASH'
          with zipfile.ZipFile(io.BytesIO(b)) as z:
              assert all(not n.startswith('/') and '..' not in pathlib.PurePosixPath(n).parts for n in z.namelist())
              z.extractall(pathlib.Path(os.environ['RUNNER_TEMP'])/'state-nextstate-v2-code')
          PY
      - name: Authorized Development temporary raw and frozen export
        env:
          JQUANTS_API_KEY: ${{ secrets.JQUANTS_API_KEY }}
          STATE9_AUDIT_RAW: ${{ runner.temp }}/state-nextstate-v2-raw
          STATE9_AUDIT_OUT: ${{ runner.temp }}/state-nextstate-v2-evidence
        run: python "$RUNNER_TEMP/state-nextstate-v2-code/export_expansion.py"
      - name: Purge exact temporary directory
        if: always()
        run: |
          python - <<'PY'
          import pathlib,os,shutil,json
          raw=pathlib.Path(os.environ['RUNNER_TEMP'])/'state-nextstate-v2-raw'
          if raw.exists():shutil.rmtree(raw)
          out=pathlib.Path(os.environ['RUNNER_TEMP'])/'state-nextstate-v2-evidence';out.mkdir(exist_ok=True)
          (out/'WORKFLOW_PURGE_RECEIPT.json').write_text(json.dumps({'verified':not raw.exists(),'secret_export':0})+'\\n')
          PY
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: state-nextstate-v2-development-${{ github.run_id }}
          path: ${{ runner.temp }}/state-nextstate-v2-evidence
          retention-days: 7
'''.replace('PAYLOAD_HASH',sha(payload))
(R/'state-nextstate-v2-20261002.yml').write_text(workflow)
old=json.loads((V/'WORKFLOW_PREFLIGHT.json').read_text());branch='state-predictiveness-v2-nextstate-20261002-v1'
assert all(not any(fnmatch.fnmatchcase(branch,b) for b in x['triggers'].get('push',{}).get('branches',[])) for x in old['all_trigger_records'] if isinstance(x['triggers'].get('push'),dict) and x['triggers']['push'].get('branches'))
(R/'WORKFLOW_PREFLIGHT.json').write_text(json.dumps({'inherited_parent_identity':'7e3ce89cb2928d46f66d4606e1010ba3a3a1896f','prior_preflight_SHA256':sha(V/'WORKFLOW_PREFLIGHT.json'),'existing_workflows_changed':0,'fanout':1,'branch':branch,'no_PR':True,'old88incident_retained':True},indent=2)+'\n')
print(json.dumps({'payload_bytes':payload.stat().st_size,'payload_SHA256':sha(payload),'files':len(list(T.rglob('*')))}))
