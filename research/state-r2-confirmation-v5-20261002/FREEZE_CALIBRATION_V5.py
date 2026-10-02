from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,hashlib,csv
R=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 audit=json.loads((R/'AUDIT_CALIBRATION_RESEARCH_V5.json').read_text());assert audit['status']=='PASS' and audit['mismatch_N']==0
 with (R/'V5_CALIBRATION_RESEARCH_EXPOSED_ONLY.csv').open() as f:rows=list(csv.DictReader(f))
 r={x['calibrated']:x for x in rows if x['model']=='R2' and x['fold']=='ALL'}
 obj={'JST':datetime.now(timezone(timedelta(hours=9))).isoformat(),'method':'ROLLING_INNER_OOF_TEMPERATURE_V1','hashes':{n:sha(R/n) for n in ['MODEL_V5.py','V5_CALIBRATION_DESIGN.md','CALIBRATION_RESEARCH_PRECOMMIT_V5.json','RESEARCH_CALIBRATION_V5.py','AUDIT_RESEARCH_V5.py','AUDIT_CALIBRATION_RESEARCH_V5.json','CALIBRATION_RESEARCH_OOF_V5.jsonl','V5_CALIBRATION_RESEARCH_EXPOSED_ONLY.csv']},'fit_scope':'V4_EXPOSED_ONLY_NOT_FRESH','research_fits':36,'fresh_labels_before_freeze':0,'research_independent_mismatch_N':0,'additional_calibration_families':0,'research_R2_raw_date_LL':float(r['False']['date_equal_LL']),'research_R2_cal_date_LL':float(r['True']['date_equal_LL']),'research_R2_LL_relative_worsening':float(r['True']['date_equal_LL'])/float(r['False']['date_equal_LL'])-1,'research_R2_Brier_relative_worsening':float(r['True']['Brier'])/float(r['False']['Brier'])-1,'research_performance_limitations_retained':True,'research_result_used_to_promote':False,'result_driven_design_changes':0,'outer_test_selection':0,'subsequent_method_search':0,'fresh_method_already_fixed_even_if_research_worse':True}
 p=R/'V5_CALIBRATION_METHOD_FREEZE.json';assert not p.exists();p.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps({k:obj[k] for k in ['method','research_fits','research_R2_LL_relative_worsening','research_R2_Brier_relative_worsening','result_driven_design_changes']}))
if __name__=='__main__':main()
