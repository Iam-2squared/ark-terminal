"""Mechanical repackage of pinned V4 exact input/kernel with fixed109 wrapper."""
from pathlib import Path
import json,hashlib,zipfile,base64,ast
R=Path(__file__).resolve().parent;T=R/'runner';OLD=R.parent/'state_predictiveness_v4_confirmation_20261002_v1';PREFIX='research/state-r2-confirmation-v5-20261002/'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def main():
 archive=OLD/'ACQUISITION_PAYLOAD_V4.zip';assert sha(archive)=='32b2ed7f8d26eb6caf311744afe27e836f20a491bedde9c719f9d81121dabcbe'
 with zipfile.ZipFile(archive) as z:
  for info in z.infolist():
   if info.is_dir() or info.filename in ['export_expansion_v4.py','metadata_universe.py','ACQUISITION_EXPANSION_PRECOMMIT.json']:continue
   dest=T/info.filename;dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(z.read(info))
 cfg=json.loads((T/'config.json').read_text());cfg['maxrequests']=900;save(T/'config.json',cfg)
 source=(T/'acquisition_base.py').read_text();before="time.sleep(1.1);requests+=1\n  assert requests<=CFG['maxrequests'],'PROVIDER_REQUEST_CAP'";after="assert requests<CFG['maxrequests'],'PROVIDER_REQUEST_CAP'\n  time.sleep(1.1);requests+=1";assert source.count(before)==1;source=source.replace(before,after);(T/'acquisition_base.py').write_text(source)
 (T/'FRESH_REACQUISITION_SCOPE_FREEZE_V5.json').write_bytes((R/'FRESH_REACQUISITION_SCOPE_FREEZE_V5.json').read_bytes())
 frozen={'scope_SHA256':sha(T/'FRESH_REACQUISITION_SCOPE_FREEZE_V5.json'),'parent_payload_SHA256':sha(archive),'code_hashes':{str(p.relative_to(T)):sha(p) for p in sorted(T.rglob('*')) if p.is_file() and (p.suffix=='.py' or p.name in ['profile.json','source_snapshot.json','config.json','FEATURE_SCHEMA_V2.json'])},'new_label_cap':0,'fit_cap':0,'bootstrap_cap':0,'HTTP_cap':900,'kernel_cap':40000,'bounded_passes':1,'counter_guard_repair':'Reject cap before increment/HTTP; no phantom request charge','original109_order':True}
 save(T/'RETRY_EXECUTION_FREEZE_V5.json',frozen);save(R/'RETRY_EXECUTION_FREEZE_V5.json',frozen)
 for p in T.rglob('*.py'):ast.parse(p.read_text())
 payload=R/'ACQUISITION_PAYLOAD_V5.zip'
 with zipfile.ZipFile(payload,'x',zipfile.ZIP_DEFLATED) as z:
  for p in sorted(T.rglob('*')):
   if p.is_file() and '__pycache__' not in str(p):z.write(p,str(p.relative_to(T)))
 (R/'ACQUISITION_PAYLOAD_V5.b64').write_text(base64.b64encode(payload.read_bytes()).decode()+'\n')
 workflow=(OLD/'state-confirmation-v4-20261002.yml').read_text()
 for a,b in [('State Predictiveness V4 Fixed Development Expansion','State Predictiveness V5 Fixed109 Recovery'),('state-predictiveness-v4-confirmation-20261002-v1','state-predictiveness-v5-r2-confirmation-20261002-v1'),('state-confirmation-v4-20261002','state-r2-confirmation-v5-20261002'),('state-reversal-v4-','state-r2-v5-'),('export_expansion_v4.py','export_recovery_v5.py'),('state-predictiveness-v4-development-','state-predictiveness-v5-recovery-'),('Fixed approved Development metadata then temporary raw current-slot export','Fixed109 approved Development recovery; no labels'),('32b2ed7f8d26eb6caf311744afe27e836f20a491bedde9c719f9d81121dabcbe',sha(payload))]:workflow=workflow.replace(a,b)
 (R/'state-r2-confirmation-v5-20261002.yml').write_text(workflow)
 save(R/'WORKFLOW_PREFLIGHT_V5.json',{'dedicated_branch':'state-predictiveness-v5-r2-confirmation-20261002-v1','fanout':1,'max_runs':2,'bounded_passes':1,'existing_workflows_changed':0,'new_label_cap':0,'payload_SHA256':sha(payload),'workflow_SHA256':sha(R/'state-r2-confirmation-v5-20261002.yml'),'old88workflow_incident_retained':True})
 print(json.dumps({'tree_elements':[{'path':'.github/workflows/state-r2-confirmation-v5-20261002.yml','type':'blob','mode':'100644','content':workflow},{'path':PREFIX+'payload.b64','type':'blob','mode':'100644','content':(R/'ACQUISITION_PAYLOAD_V5.b64').read_text()}]}))
if __name__=='__main__':main()
