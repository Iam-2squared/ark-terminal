"""One reproduction campaign, saved scores/assignment only, no fitting or rescoring."""
import json,pathlib,subprocess,sys,hashlib
def pin(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def main():
    root=pathlib.Path(__file__).resolve().parents[1];mark=root/'reproduction/CAMPAIGN_STARTED.json';assert not mark.exists(),'REPRODUCTION_BUDGET_ALREADY_USED';mark.parent.mkdir(parents=True,exist_ok=True);mark.write_text('{"reproductionCampaign":1}\n')
    subprocess.run([sys.executable,str(root/'implementation/assign_ranks.py'),'reproduce'],check=True)
    original=root/'private/SEALED_RANK_ASSIGNMENTS.jsonl.gz';repeat=root/'reproduction/SEALED_RANK_ASSIGNMENTS.jsonl.gz';assert original.read_bytes()==repeat.read_bytes()
    subprocess.run([sys.executable,str(root/'implementation/evaluate_ranks.py'),'reproduce'],check=True)
    members=[]
    for p in sorted((root/'evaluation').rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(root/'evaluation');q=root/'reproduction/evaluation'/rel;assert p.read_bytes()==q.read_bytes(),str(rel);members.append({'path':str(rel),**pin(p.read_bytes())})
    receipt={'status':'PASS','reproductionCampaign':1,'failed_attempt_N':0,'saved_assignment_exact_match':True,'assignment_pin':pin(original.read_bytes()),'aggregate_and_evaluation_payload_exact_match_N':len(members),'aggregate_and_evaluation_payload_pins':members,'model_fit':0,'model_refit':0,'score_reinference':0,'threshold_or_policy_changes':0,'comparison':'exact bytes, SHA256, Git blob identity','same_author':True}
    (root/'public/REPRODUCTION_RECEIPT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k!='aggregate_and_evaluation_payload_pins'}))
if __name__=='__main__':main()
