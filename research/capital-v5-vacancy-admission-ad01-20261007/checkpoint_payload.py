from pathlib import Path
import json,hashlib,sys
R=Path(__file__).resolve().parent;w=sys.argv[1];P=R/'public'
def pin(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def save(p,x):p.write_text(json.dumps(x,sort_keys=True,indent=2,ensure_ascii=False)+'\n')
arms={}
for arm in ['E0','H1','H2']:
 p=R/'baseline/private/runs'/w/'E/RESULT.json' if arm=='E0' else R/'private/runs'/w/arm/'RESULT.json'
 x=json.loads(p.read_text());arms[arm]={k:x[k] for k in ['status','final_equity','profit','return_pct','funded_N','closed_N','SHARP_DROP_fill_N','SHARP_DROP_intent_N','completed_session_N','start_session','end_session','planned_sessions','calendar_span_inclusive_days']}
save(P/(w+'_PATH_STATUS.json'),{'window_id':w,'arms':arms,'mainCapital':'CAPITAL_MAX3_SLOT_RESERVE_V1','mainExit':'SHARP_DROP_FIRST_OBSERVED_EXIT_V0','selectedAdmissionCandidate':None})
x=json.loads((P/'CURRENT_STATE.json').read_text());completed=[v for v in [f'W{i:02}' for i in range(13,22)]+['CHAIN38'] if all((R/'private/runs'/v/a/'RESULT.json').exists() for a in ['H1','H2'])];remaining=[v for v in [f'W{i:02}' for i in range(13,22)]+['CHAIN38'] if v not in completed];x.update(status='PRIMARY_WINDOW_CHECKPOINT' if w!='CHAIN38' else 'FORMAL_CAMPAIGN_COMPLETE_AUDIT_PENDING',completed_window_paths=completed,uncompleted_windows=remaining,next_command=f'python work/ad01/implementation/campaign_ad01.py formal --window {remaining[0]} --policy H1' if remaining else 'python work/ad01/independent_ad01.py --run-campaign',formal_candidate_path_N=len(completed)*2);save(P/'CURRENT_STATE.json',x)
save(P/(w+'_CHECKPOINT_STATE.json'),x)
e=json.loads((P/'EXECUTION_AND_REPAIR_RECEIPT.json').read_text());e['formal_candidate_paths_completed']=len(completed)*2;save(P/'EXECUTION_AND_REPAIR_RECEIPT.json',e)
paths=[P/(w+'_PATH_STATUS.json'),P/'CURRENT_STATE.json',P/(w+'_CHECKPOINT_STATE.json'),P/'EXECUTION_AND_REPAIR_RECEIPT.json']
print(json.dumps({'public_files':[{'path':p.name,'content':p.read_text(),**pin(p)} for p in paths],'manifest':json.loads((R/'publication'/w/(w+'_MANIFEST.json')).read_text()),'manifest_content':(R/'publication'/w/(w+'_MANIFEST.json')).read_text(),'results':{a:arms[a]['final_equity'] for a in arms}},ensure_ascii=False))
