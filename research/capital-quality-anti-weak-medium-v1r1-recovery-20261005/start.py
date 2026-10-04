from control import *

def main():
    old=read(OLD/'CLOSURE.json');b=basis()
    assert b['HEAD']==OLD_HEAD and b['branch']==BRANCH
    assert old['qualityStatus']=='QUALITY_CONTRACT_FAIL' and old['terminal_checkpoint']=='Q12_CLOSURE_FIXED_STOP'
    assert b['old_branch_actual_GET']['HEAD']==OLD_HEAD and len(b['old_required_actual_GET'])==13
    save(OUT/'OLD_CYCLE_READ_ONLY_AUTHORITY.json',{'exact_jst':now(),'status':'PASS','old_head':OLD_HEAD,
        'old_tree':b['tree'],'old_status':old['qualityStatus'],'terminal':old['terminal_checkpoint'],
        'old_required_actual_GET':b['old_required_actual_GET'],'research_change_after_old_fixed_HEAD':0,
        'broken_Q4_metric_input':False,'broken_Q4_repair':False,'old_expected_hash_reproduction':False,
        'required_local_source_sha256':{x['path']:sha(OLD/x['path']) for x in b['old_required_actual_GET']},
        'old_corrupt_Q4_incident_only_sha256':sha(OLD/'ZERO_FIT_BASELINE.json'),
        'old_frozen_metrics_code_sha256':sha(OLD_METRICS)})
    save(OUT/'ALLOCATION_FIREWALL.json',{'exact_jst':now(),'base':OLD_HEAD,'base_branch':'capital-quality-vnext-20261005',
        'branch':BRANCH,'old_firewall_sha256':sha(OLD/'ALLOCATION_FIREWALL.json'),
        'allowed':['v7 or earlier shared authorities','Frozen Rank vNext pP','Movement feature/preprocessing contract','teacher support/common mask','old Quality read-only completed artifacts'],
        'forbidden':['Main v8/v8R1 research results','B1/B2 outcomes','Capital results','blocked-winner anatomy','Main research import/export','Main rebase/merge'],
        'v8_research_result_read':0,'v8r1_research_result_read':0,'main_b1_b2_outcome_imported':0,
        'quality_results_exported_to_main':0,'main_branch_get':0,'metadata_only_conflict_reads':0,
        'new_fits':0,'Safety':SAFETY})
    checkpoint('R0_START_NEW_CYCLE_AND_FIREWALL',['old actual HEAD exact; old Q12 fail immutable; independent new branch from old Quality only'],
        {'old_status':'QUALITY_CONTRACT_FAIL','base_HEAD':OLD_HEAD,'Main_research_reads':0},'R1 authenticate all private pack hashes and completed fits; never refit')
    print('R0 complete')

if __name__=='__main__':main()
