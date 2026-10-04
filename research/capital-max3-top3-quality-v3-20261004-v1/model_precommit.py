"""Pin code and fixed LR environment before fit. No performance reads."""
import ast,sys
import sklearn,numpy
from checkpoint import *
code=Path(__file__).parent
names=['core_features.py','preprocessing.py','train_heads.py','freeze_scores.py','quality.py','allocation.py','replay.py','execution.py','independent_audit.py','test_canaries.py','io_data.py']
for n in names:ast.parse((code/n).read_text())
old=ROOT/'research/capital-vnext-v2-movement-20261004-v1/model.py'
s=old.read_text();tree=ast.parse(s);lines=s.splitlines(keepends=True);new=(code/'preprocessing.py').read_text();nt=ast.parse(new);nl=new.splitlines(keepends=True)
for fun in ('transform','predict_saved'):
 a=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==fun);b=next(n for n in nt.body if isinstance(n,ast.FunctionDef) and n.name==fun)
 assert ''.join(lines[a.lineno-1:a.end_lineno])==''.join(nl[b.lineno-1:b.end_lineno])
assert sha(code/'execution.py')==sha(ROOT/'research/capital-max3-liquidity-off-20261004-v1/execution.py')
save(OUT/'MODEL_PRECOMMIT_CODE_PIN.json',{'jst':now(),'model':'sklearn LogisticRegression','config':json.loads((OUT/'DESIGN_PRECOMMIT.json').read_text())['model'],'environment':{'python':sys.version,'sklearn':sklearn.__version__,'numpy':numpy.__version__},'CORE_preprocessing_function_byte_identity':True,'execution_code_byte_identity':True,'runtime_code_hashes':{n:sha(code/n) for n in names},'CORE_manifest_hash':sha(OUT/'CORE_FEATURE_MANIFEST.json'),'CORE_runtime_hash':sha(PRIVATE/'CORE_RUNTIME_CAUSAL.jsonl.gz'),'H5_hash':sha(V2/'CORE_P5_SCORE_STREAM.jsonl.gz'),'new_fits':24,'H5_new_fits':0,'fit_counts_before_start':0,'hyperparameter_sweep':0,'feature_search':0,'threshold_search':0,'safety':SAFETY})
checkpoint('Q3_MODEL_PRECOMMIT_CODE_PIN','CODE_MODEL_CONTRACT_PINNED_BEFORE_FIT',{'new_fit_budget':24,'H5_fit_budget':0,'runtime_code_files':len(names),'model_available':'sklearn fixed LR','all_replays':4},next_direction='Fit exactly8 past-only blocks for each H3/HF1/HL0; no test teacher payload access before fit.')
