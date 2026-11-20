"""Run the unchanged sealed FIRST threshold machine on corrected OOF, fit=0."""
from repair_utils import *
import first_entry

def run():
 assert read(HERE/'CORRECTED_OOF_LINEAGE_RECEIPT.json')['mixed_old_bug_Q_D_predictions']==0
 # Only artifact destination/input bundle changes. Function bodies, watch,
 # canonical next-open fill, and future evaluator retain exact frozen semantics.
 assert sha(HERE/'first_entry.py')==sha(BASE/'first_entry.py')
 first_entry.HERE=HERE
 first_entry.generate()
 first_entry.fill_and_evaluate()
 rs=[r for r in rows(HERE/'FIRST_ENTRY_Q70.jsonl.gz') if r['family']=='P1']
 assert len(rs)==2155 and len({r['watch_key'] for r in rs})==2155
 assert all(r['decision_after_first_entry']==r['second_intent']==r['EXIT_calls']==r['reentry_calls']==0 for r in rs)
 write_rows(HERE/'P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz',rs)
 print(json.dumps({'Primary_Freeze_Target':'P1_Q70','FIRST_ENTRY_N':sum(r['entry_status']=='FIRST_ENTRY' for r in rs),'watch_records':len(rs),'policy_reselection':0,'EXIT':0,'Reentry':0,'Capital':0,'new_fits':0}))

if __name__=='__main__':run()
