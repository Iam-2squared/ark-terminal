"""Bulk mechanical relocation of frozen research math; originals unchanged."""
from pathlib import Path
import shutil,ast
R=Path(__file__).resolve().parent;P=Path('/workspace/scratch/a1e749e0bd6c/state_predictiveness_v3_reversal_20261002_v1')
shutil.copyfile(P/'BUILD_V3.py',R/'INHERITED_TARGET_ANATOMY_V3.py')
src=(P/'FIT_V3.py').read_text().replace('PREDICTIVENESS_V3_REVERSAL_PRECOMMIT.json','PREDICTIVENESS_V4_PRECOMMIT.json').replace('FEATURE_SCHEMA_V3.json','FEATURE_SCHEMA_V4.json').replace('SPLIT_REALIZED_V3.json','SPLIT_REALIZED_V4.json').replace('DATASET_MANIFEST.json','DATASET_MANIFEST_V4.json').replace('2026100302','2026100402').replace('PERMUTATION_MAPPING_V3','PERMUTATION_MAPPING_V4').replace('TARGET_CONTROL_AVAILABILITY_V3','TARGET_CONTROL_AVAILABILITY_V4').replace('FIT_INDEX_V3','FIT_INDEX_V4')
# Empty fixed folds are retained, never refolded. Insufficient initial dates => explicit unavailable fold.
src=src.replace("if not train or not test:","if not train or not test or not fold['initial_train_dates_sufficient']:")
src=src.replace(" assert not (R/'OOF_ALL.jsonl').exists(),'OOF_ALREADY_FIXED'", " assert not (R/'OOF_ALL.jsonl').exists(),'OOF_ALREADY_FIXED'\n if not (R/'MODEL_EXECUTION_LEDGER.jsonl').exists():(R/'MODEL_EXECUTION_LEDGER.jsonl').touch()")
(R/'FIT_V4.py').write_text(src)
src=(P/'METRICS_V3.py').read_text()
mapping={'DATASET_MANIFEST.json':'DATASET_MANIFEST_V4.json','REVERSAL_METRICS_AGGREGATE.csv':'REVERSAL_METRICS_AGGREGATE_V4.csv','REVERSAL_METRICS_BY_FOLD.csv':'REVERSAL_METRICS_BY_FOLD_V4.csv','REVERSAL_PER_CLASS_METRICS.csv':'REVERSAL_PER_CLASS_METRICS_V4.csv','REVERSAL_CONFUSION_MATRIX.csv':'REVERSAL_CONFUSION_MATRIX_V4.csv','CALIBRATION_METRICS.csv':'CALIBRATION_METRICS_V4.csv','CALIBRATION_BUCKETS.csv':'CALIBRATION_BUCKETS_V4.csv','NEXTSTATE_9CLASS_V3.csv':'NEXTSTATE_9CLASS_V4.csv','CONFUSION_MATRIX_9STATE_V3.csv':'CONFUSION_MATRIX_9STATE_V4.csv','PER_STATE_PRECISION_RECALL_F1_V3.csv':'PER_STATE_PRECISION_RECALL_F1_V4.csv','UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE.csv':'UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE_V4.csv','DOWN_TO_UP_FALSE_NEGATIVE.csv':'DOWN_TO_UP_FALSE_NEGATIVE_V4.csv','PATH_ANATOMY_SUPPORT_SUMMARY.csv':'PATH_ANATOMY_SUPPORT_SUMMARY_V4.csv','NEGATIVE_CONTROL_V3.csv':'NEGATIVE_CONTROL_V4.csv','SHIFT60_STRESS_V3.csv':'SHIFT60_STRESS_V4.csv','R0_R1_R2_R3_R4_INCREMENTAL.csv':'R0_R1_R2_R3_R4_INCREMENTAL_V4.csv',"f'REVERSAL_PATH_ANATOMY_LENGTH{length}.csv'":"f'PATH_ANATOMY_LENGTH{length}_V4.csv'"}
for old,new in mapping.items():src=src.replace(old,new)
src=src.replace('absolute=bv is not None and bv<=av','absolute=bv is not None and av is not None and bv<=av+1e-12')
src=src.replace("'TRUE_NULL_PROMOTION_VETO'", "'TRUE_NULL_PRIMARY_INTEGRITY_FAILURE_IF_CALIBRATED_CONTEXT'")
src=src.replace('def csvout(n,rows):','def csvout(n,rows,columns=None):').replace("fieldnames=list(rows[0]) if rows else ['status']", "fieldnames=list(rows[0]) if rows else columns or ['status']")
src=src.replace("csvout(f'PATH_ANATOMY_LENGTH{length}_V4.csv',table)","csvout(f'PATH_ANATOMY_LENGTH{length}_V4.csv',table,['length','sequence','history_complete','N','date_N','security_N','supported_descriptive_sequence']+[c+s for c in CLASSES['CONTEXT_REVERSAL'] for s in ['_N','_rate','_CI95_low','_CI95_high','_valid_global_draws']])")
start=src.index('    gates=[];promoted=[]');end=src.index("if __name__=='__main__':main()")
src=src[:start]+"    import ASSESS_V4\n    import sys\n    ASSESS_V4.main(sys.modules[__name__],groups,controls)\n"+src[end:]
(R/'METRICS_V4.py').write_text(src)
src=(P/'INDEPENDENT_AUDIT_V3.py').read_text()
for old,new in mapping.items():src=src.replace(old,new)
for old,new in [('PREDICTIVENESS_V3_REVERSAL_PRECOMMIT','PREDICTIVENESS_V4_PRECOMMIT'),('FEATURE_SCHEMA_V3','FEATURE_SCHEMA_V4'),('SPLIT_REALIZED_V3','SPLIT_REALIZED_V4'),('SPLIT_PLAN_V3','SPLIT_PLAN_V4'),('PERMUTATION_MAPPING_V3','PERMUTATION_MAPPING_V4'),('FIT_INDEX_V3','FIT_INDEX_V4'),('2026100302','2026100402'),('V3_NEW_DEV_EVAL','V4_NEW_DEV_EVAL'),('INDEPENDENT_AUDIT_V3.json','INDEPENDENT_AUDIT_V4.json')]:src=src.replace(old,new)
start=src.index("    primitive=R.parent/");end=src.index('    features={};labels={};anatomies={}',start);src=src[:start]+src[end:]
src=src.replace(';oracle.independent_feature_check(old,traces)','')
src=src.replace("        lab=list(map(json.loads,", "        import AUDIT_TRACE_PREFIX_V4\n        AUDIT_TRACE_PREFIX_V4.run(sys.modules[__name__],stream,traces)\n        lab=list(map(json.loads,")
src=src.replace('import json,csv,hashlib,math,statistics,importlib.util','import json,csv,hashlib,math,statistics,importlib.util,sys')
start=src.index('    for k,n in oracle.counts.items():');end=src.index('    donors={};',start);src=src[:start]+src[end:]
src=src.replace("'original63_features_unchanged'","'original_saved_features_unchanged'")
src=src.replace("all(r['date']<min(x['date'] for x in test) and target", "all(r['date']<fold['test_dates'][0] and target")
src=src.replace("==jread('FIT_INDEX_V4.json')['fit_operations']==576", "==jread('FIT_INDEX_V4.json')['fit_operations']")
src=src.replace("grouped[key]", "grouped.get(key,[])").replace("grouped[('CONTEXT_REVERSAL','REAL',row['model'],True)]", "grouped.get(('CONTEXT_REVERSAL','REAL',row['model'],True),[])").replace("grouped[('CONTEXT_REVERSAL','REAL','R0',True)]", "grouped.get(('CONTEXT_REVERSAL','REAL','R0',True),[])")
src=src.replace("grouped[(row['task'],row['control'],row['model'],row['calibrated']=='True')]", "grouped.get((row['task'],row['control'],row['model'],row['calibrated']=='True'),[])")
src=src.replace("bm['date_equal_log_loss']<=am['date_equal_log_loss']", "am['date_equal_log_loss'] is not None and bm['date_equal_log_loss']<=am['date_equal_log_loss']+1e-12")
start=src.index("    for row in cread('PROMOTION_GATE_V3.csv'):");end=src.index("    caps=jread('BUDGET_START_V3.json')",start);src=src[:start]+"    import AUDIT_SUPPLEMENT_V4\n    expected=AUDIT_SUPPLEMENT_V4.run(sys.modules[__name__],grouped,features,ratio,ci)\n"+src[end:]
src=src.replace("caps=jread('BUDGET_START_V3.json')['V3_caps']", "caps=jread('BUDGET_START_V4.json')['finite_caps']")
start=src.index("    metric=metric_ref(primary");end=src.index("    result={",start);src=src[:start]+"    metric=metric_ref(primary,classes['CONTEXT_REVERSAL'])[0]\n"+src[end:]
src=src.replace("'primitive_oracle_SHA256':sha(primitive)","'independent_source_SHA256':sha(Path(__file__))")
src=src.replace('Inherited independent primitive feature oracle verified by hash.','Frozen State9/Path full semantic kernel re-audit deliberately not rerun; source/trace identity and prefix anatomy audited.')
(R/'INDEPENDENT_AUDIT_V4.py').write_text(src)
for n in ['BUILD_V4.py','FIT_V4.py','INHERITED_TARGET_ANATOMY_V3.py']:ast.parse((R/n).read_text())
print('Inherited target/anatomy byte copy and model-math relocation ready; labels/fits/draws0.')
