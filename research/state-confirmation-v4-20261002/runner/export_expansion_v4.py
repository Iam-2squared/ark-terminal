from pathlib import Path
import os,json,hashlib,shutil,subprocess,traceback,sys
from fractions import Fraction
import acquisition_base as a
from input_gate import map_rows,scheduled_minutes
import normalize80,normalize120
from PATH_FROZEN import PathBuilder
from CAUSAL_FEATURE_BUILDER import FeatureBuilder
from metadata_universe import build as metadata_build
H=Path(__file__).resolve().parent;OUT=a.OUT;RAW=a.RAW;cfg=a.CFG
schema=json.loads((H/'FEATURE_SCHEMA_V2.json').read_text())
steps=0;completed=0;children=[];datasets=[];ledger=[];status='NOT_STARTED';error=None
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):a.write(OUT/n,x)
def safe(ex):
    code=str(ex)
    return code if code and all(c.isupper() or c.isdigit() or c=='_' for c in code) else 'SANITIZED_TECHNICAL_EXCEPTION'
def flush():
    save('DEVELOPMENT_COMPLETION_LEDGER.json',ledger)
    save('DATASET_MANIFEST.json',{'pairs':datasets,'features_completed_before_label_builder':True,'endpoint_N':sum(p['scheduled_endpoints_N'] for p in datasets),'new_kernel_steps':steps,'new_provider_requests':a.requests})
try:
    pre=json.loads((H/'ACQUISITION_EXPANSION_PRECOMMIT.json').read_text())
    ss=json.loads((H/'source_snapshot.json').read_text())
    for n in ['candidate/api.py','candidate/exact.py','candidate/kernel.py','profile.json']:assert sha(H/n)==ss[n],'FROZEN_IDENTITY'
    assert bool(os.environ.get('JQUANTS_API_KEY')),'BINDING_UNAVAILABLE'
    universe=metadata_build(H,save);proposals=universe['proposals'];allowed={(x['date'],x['previous']) for x in cfg['acquisition_session_scope']};exc={(r['date'],r['code']) for r in cfg['exclusion_pairs']}
    assert len(proposals)<=318,'PROPOSAL_CAP'
    save('ACQUISITION_EXPANSION_PRECOMMIT.json',pre)
    provider_stopped=universe['provider_stopped']
    for k in range(1,len(proposals)+1):
        pair=proposals[k-1];pid=f'V4N{k:03d}';d,p,c=pair['date'],pair['previous'],pair['code']
        assert (d,p) in allowed and (d,c) not in exc and (p,c) not in exc,'SCOPE_OR_EXPOSURE_BOUNDARY'
        entry={'proposal_ordinal':k,'pair_id':pid,'date':d,'security_id':pair['security_id'],'session_id':pair['session_id'],'status':None,'reason':None,'replacement':0}
        ledger.append(entry)
        if provider_stopped:
            entry.update(status='PROVIDER_FAILURE',reason=provider_stopped,request_attempted=False);flush();continue
        try:
            entry['request_attempted']=True
            cur=a.fetch(d,'minute',c);prev=a.fetch(p,'minute',c)
            good,why=a.good(cur);goodp,whyp=a.good(prev)
            if not good or not goodp:
                entry.update(status='RAW_UNAVAILABLE' if why=='NO_MINUTE_ROWS' or whyp=='NO_MINUTE_ROWS' else 'INVALID_SESSION',reason=why or whyp);flush();continue
            if a.adjacency(prev)==0:
                entry.update(status='U_UNAVAILABLE',reason='NO_PREVIOUS_ADJACENT_RETURNS');flush();continue
            # Convert parser's Token subclass to the original exact plain lexeme, no numeric conversion.
            cur=[{**r,**{f:str(r[f]) for f in ['O','H','L','C']}} for r in cur]
            prev=[{**r,**{f:str(r[f]) for f in ['O','H','L','C']}} for r in prev]
            try:
                mapped=map_rows(cur);norm=normalize80.generate(prev,mapped);ref=normalize120.regenerate(prev,mapped)
            except ValueError as ex:
                code=safe(ex)
                if code=='U_UNAVAILABLE':entry.update(status='U_UNAVAILABLE',reason=code);flush();continue
                raise
            assert all(norm[x]==ref[x] for x in ['U','P_ref','coordinates','previous_return_pairs_N','previous_pair_ids']),'M0_80_120_MISMATCH'
            look={m['t']:(m,x) for m,x in zip(mapped,norm['coordinates'])};schedule=scheduled_minutes(d)
            trade=[m for m in schedule if m not in (691,931 if d>='2024-11-05' else 901)];ti={m-540:i for i,m in enumerate(trade)}
            sandbox=RAW/'workers'/pid;sandbox.mkdir(parents=True)
            shutil.copytree(H/'candidate',sandbox/'candidate');shutil.copyfile(H/'profile.json',sandbox/'profile.json');shutil.copyfile(H/'engine_stream.py',sandbox/'engine_stream.py')
            child=subprocess.Popen([sys.executable,'engine_stream.py'],cwd=sandbox,env={'PATH':os.environ['PATH'],'LANG':'C.UTF-8','PYTHONHASHSEED':'0','PYTHONIOENCODING':'utf-8'},stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1);children.append(child)
            path=PathBuilder(pid);fb=FeatureBuilder(schema)
            ft=OUT/'FEATURES'/f'{pid}.jsonl';st=OUT/'STATE9_TRACES'/f'{pid}.jsonl';ep=OUT/'PATH_ENDPOINTS'/f'{pid}.jsonl'
            for f in [ft,st,ep]:f.parent.mkdir(parents=True,exist_ok=True)
            observed=0
            with ft.open('x') as f,st.open('x') as s,ep.open('x') as e:
                for m in schedule:
                    t=m-540;found=look.get(t);raw=None if found is None else {'t':t,'known_at':t,'source':found[0]['source'],'auction':found[0]['auction'],**{x.lower():found[1][x] for x in ['O','H','L','C']}}
                    steps+=1;assert steps<=110000,'KERNEL_CAP'
                    child.stdin.write(json.dumps({'t':t,'raw':raw,'case_id':pid})+'\n');child.stdin.flush();line=child.stdout.readline();assert line,'WORKER_STOP';state=json.loads(line)
                    assert state['as_of']==t and (state['observed_at'] is None or state['observed_at']<=t),'STATE_FUTURE'
                    if raw is not None and state['numeric_status']=='ACCEPTED':assert Fraction(state['close_u'])==Fraction(raw['c']),'CLOSE_MAPPING'
                    end=d+'T'+f'{m//60:02d}:{m%60:02d}:00+09:00';slot={'scheduled_t':t,'bar_end':end,'row_status':'OBSERVED' if found else 'UNKNOWN_GAP'}
                    before=len(path.events);endpoint=path.push(state,slot);events=path.events[before:];features=fb.push(state,endpoint,events,path.runs);observed+=int(state['current_semantics_observed'])
                    row={'row_key':pair['security_id']+'|'+pair['session_id']+'|'+end,'pair_id':pid,'security_id':pair['security_id'],'session_id':pair['session_id'],'date':d,'bar_end':end,'scheduled_t':t,'tradable_index':ti.get(t),'causal_segment_id':endpoint['causal_segment_id'],'run_id':endpoint['run_id'],'source_pointer':None if found is None else found[0]['_source'],'feature_max_timestamp':end,'feature_created_before_target':True,'features':features,'audit_source':{'Close_JPY':None if found is None else found[0]['C'],'x_C':None if found is None else found[1]['C'],'U':norm['U'],'numeric_status':state['numeric_status'],'raw_present':found is not None,'auction':None if found is None else found[0]['auction'],'source':None if found is None else found[0]['source'],'observed':state['current_semantics_observed'],'formal_primary':endpoint['Primary_or_null'],'local_direction':state['leg_direction'],'events':[{x:v[x] for x in ['event_type','scheduled_t','bar_end','causal_segment_id','from_primary_or_null','to_primary_or_null']} for v in events]}}
                    for writer,obj in [(f,row),(s,state),(e,endpoint)]:writer.write(json.dumps(obj,sort_keys=True,separators=(',',':'))+'\n')
            child.stdin.close();assert child.wait(timeout=30)==0,'WORKER_FAILURE';completed+=1
            datasets.append({**pair,'pair_id':pid,'scheduled_endpoints_N':len(schedule),'raw_current_N':len(mapped),'raw_previous_N':len(prev),'observed_semantic_N':observed,'formal_null_N':len(schedule)-observed,'feature_SHA256':sha(ft),'state_trace_SHA256':sha(st),'path_endpoint_SHA256':sha(ep),'U':norm['U'],'price_basis':'UNADJUSTED_JPY','source_identity':hashlib.sha256(json.dumps([r['_source'] for r in cur+prev],sort_keys=True).encode()).hexdigest(),'trace_mode':'FROZEN_CURRENT_SLOT_GENERATION_V4'})
            save('M0_RECEIPTS/'+pid+'.json',{'U':norm['U'],'P_ref':norm['P_ref'],'previous':p,'precision80_120_match':True,'previous_return_pairs_N':norm['previous_return_pairs_N'],'previous_pair_ids':norm['previous_pair_ids']})
            entry.update(status='ACQUIRED',reason=None,observed_N=observed);flush()
            print(json.dumps({'proposal_ordinal':k,'status':entry['status'],'completed':completed,'requests':a.requests,'labels_created':0}),flush=True)
        except Exception as ex:
            code=safe(ex)
            # Actual integrity errors are not downgraded to acquisition skips.
            if code in ['M0_80_120_MISMATCH','FROZEN_IDENTITY','STATE_FUTURE','CLOSE_MAPPING','KERNEL_CAP','PROTECTED_BOUNDARY','CROSS_DATE','CROSS_CODE','EXACT_TOKEN_MISSING']:
                raise
            if code.startswith('PROVIDER_') or code=='BINDING_UNAVAILABLE':
                entry.update(status='PROVIDER_FAILURE',reason=code)
                if code in ['PROVIDER_HTTP_401','PROVIDER_HTTP_403','PROVIDER_HTTP_429','PROVIDER_REQUEST_CAP']:provider_stopped=code
            else:entry.update(status='OTHER_EXPLICIT_REASON',reason=code,error_type=type(ex).__name__)
            # Incomplete output from a failed technical pair cannot enter the dataset.
            for sub in ['FEATURES','STATE9_TRACES','PATH_ENDPOINTS']:
                partial=OUT/sub/f'{pid}.jsonl'
                if partial.exists():shutil.move(partial,OUT/sub/f'{pid}.INCOMPLETE.jsonl')
            for child in children:
                if child.poll() is None:child.terminate();child.wait(timeout=30)
            flush()
    status='DEVELOPMENT_COMPLETION_READY'
except Exception as ex:
    error={'type':type(ex).__name__,'code':safe(ex),'locations':[{'file':Path(f.filename).name,'line':f.lineno} for f in traceback.extract_tb(ex.__traceback__)]};status='ACQUISITION_LANE_FAILURE_LOCAL_CORPUS_REMAINS'
finally:
    for child in children:
        if child.poll() is None:child.terminate();child.wait(timeout=30)
    flush();save('SOURCE_RECEIPTS.json',a.receipts)
    save('RUNNER_FINAL_RECEIPT.json',{'status':status,'error':error,'provider_requests':a.requests,'new_steps':steps,'completed_pairs':completed,'fixed_pending_proposals':len(proposals) if 'proposals' in globals() else 0,'fixed_date_links':106,'classified':len(ledger),'future_classifier_input':0,'secret_values_exported':0,'raw_pages_exported':0,'protected_requests':0,'old16FAIL':16,'old88incident':88})
    assert RAW.name=='state-reversal-v4-raw' and RAW.parent==Path(os.environ['RUNNER_TEMP']),'PURGE_BOUNDARY'
    shutil.rmtree(RAW);save('PURGE_RECEIPT.json',{'verified':not RAW.exists(),'raw_pages_exported':0})
    save('MANIFEST.json',{'files':[{'path':str(p.relative_to(OUT)),'SHA256':sha(p),'bytes':p.stat().st_size} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='MANIFEST.json']})
    print(json.dumps({'status':status,'error':error,'purged':not RAW.exists(),'provider_requests':a.requests,'new_steps':steps}),flush=True)
if error:sys.exit(1)
