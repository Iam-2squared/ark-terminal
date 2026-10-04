from control import *

def main():
    assert read(OUT/'BASELINE_INDEPENDENT_CERTIFICATION.json')['status']=='PASS'
    names=['model_artifact_audit.py','independent_io.py']
    codes={str((CODE/n).relative_to(ROOT)):sha(CODE/n) for n in names}
    save(OUT/'MODEL_ARTIFACT_AUDIT_EXECUTION_CLAIM.json',{'exact_jst':now(),'maximum_executions':1,
        'new_fits':0,'refits':0,'audit_refits':0,'committed_before_execution':True,'actual_GET_before_execution_verified':True,
        'code_sha256':codes,'baseline_certification_sha256':sha(OUT/'BASELINE_INDEPENDENT_CERTIFICATION.json'),
        'old_artifact_reuse_freeze_sha256':sha(OUT/'COMPLETED_FITS_REUSE_FREEZE.json'),
        'optimizer_execution':0,'ambiguous_execution_policy':'STOP; inspect receipts; never refit'})
    print('model audit/join single-execution claim ready; no optimizer')

if __name__=='__main__':main()
