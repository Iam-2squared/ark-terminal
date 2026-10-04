"""Q5 claim all permitted fits before execution; restart ambiguity fails closed."""
from control import *

def main():
    assert counts()['total_fits']==0 and (OUT/'ZERO_FIT_BASELINE_FREEZE.json').exists()
    design=read(OUT/'FEATURE_MODEL_SPLIT_PRECOMMIT.json')
    claims=[]
    for block in design['split']['blocks']:
        for head,target in [('MOVE_U2','U2'),('MOVE_U3','U3')]:
            claims.append({'head':head,'target':target,'block':block['block'],'max_attempts':1,
                'training_payload_sha256':sha(PRIVATE/'training'/f"BLOCK_{block['block']:02d}_PAST_ONLY.jsonl.gz"),
                'preprocessing_authority_sha256':sha(INPUTS/'models'/f"MOVE_P_BLOCK_{block['block']:02d}.json")})
    save(OUT/'FIT_CLAIM.json',{'exact_jst':now(),'status':'CLAIMED_NOT_EXECUTED','hard_cap':16,'claims':claims,
        'completed_fit_refit':0,'ambiguous_start_without_completion':'STOP; never retry',
        'baseline_sha256':sha(OUT/'ZERO_FIT_BASELINE.json'),'design_sha256':sha(OUT/'FEATURE_MODEL_SPLIT_PRECOMMIT.json'),
        'code_sha256':{p.name:sha(p) for p in Path(__file__).parent.glob('*.py')},'counts_at_claim':counts(),'Safety':SAFETY})
    checkpoint('Q5_U2_U3_FIT_CLAIM','COMPLETE',['All16 unique head/block claims fixed before fitting',
        'Training/evaluation/code hashes pinned; one attempt per claim'],{'MOVE_U2_max':8,'MOVE_U3_max':8,'total_max':16,'fits_completed':0},'Execute only claimed fits; any ambiguity or ConvergenceWarning stops the cycle')
    print({'claims':16,'completed':0})

if __name__=='__main__':main()
