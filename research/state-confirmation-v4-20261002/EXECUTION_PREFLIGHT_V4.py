"""No labels, fits or random draws: verify inherited math relocation."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,hashlib,ast,difflib
R=Path(__file__).resolve().parent;P=Path('/workspace/scratch/a1e749e0bd6c/state_predictiveness_v3_reversal_20261002_v1')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
pre=json.loads((R/'PREDICTIVENESS_V4_PRECOMMIT.json').read_text())
for n,h in pre['hashes'].items():assert sha(R/n)==h,'PRECOMMIT_CHANGED'
assert sha(R/'INHERITED_TARGET_ANATOMY_V3.py')==pre['target_anatomy_source_SHA256'],'TARGET_ANATOMY_MATH_CHANGED'
assert sha(P/'FIT_V3.py')==pre['model_math_source_SHA256'],'PARENT_MODEL_CHANGED'
old=ast.parse((P/'FIT_V3.py').read_text());new=ast.parse((R/'FIT_V4.py').read_text())
oldf={n.name:ast.dump(n,include_attributes=False) for n in old.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))};newf={n.name:ast.dump(n,include_attributes=False) for n in new.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
names=['weights','ledger','prob','temp','loss','Encoder','build','evaluate','fit']
assert all(oldf[n]==newf[n] for n in names),'MODEL_CALIBRATION_MATH_CHANGED'
files=['BUILD_V4.py','FIT_V4.py','METRICS_V4.py','ASSESS_V4.py','INDEPENDENT_AUDIT_V4.py','AUDIT_SUPPLEMENT_V4.py','RENDER_V4.py','INHERITED_TARGET_ANATOMY_V3.py']
for n in files:ast.parse((R/n).read_text())
x={'JST':datetime.now(timezone(timedelta(hours=9))).isoformat(),'status':'PASS','all_precommit_hashes_PASS':True,'target_anatomy_byte_identical':True,'model_calibration_functions_AST_identical':names,'source_hashes':{n:sha(R/n) for n in files},'scope_split_gate_calibration_changes':0,'labels_generated':0,'fits':0,'draws':0,'scope_note':'Implementation relocation and independently coded V4 gates per fixed contract, never a new model family.'}
(R/'EXECUTION_PREFLIGHT_V4.json').write_text(json.dumps(x,sort_keys=True,indent=2)+'\n');print(json.dumps({'status':'PASS','models_and_calibration_AST_identical':True,'labels_fits_draws':[0,0,0]}))
