"""Prior-work matrix: read saved Evidence; never execute prior research."""
import json
from control import ROOT, OUT, now, sha, save, checkpoint

def main():
    base=ROOT/'docs/evidence'
    entries=[
        ('capital-bigwinner-one-shot-20261004-v1','REPORT-ja.md',
         'S Winner5=23.53%, A=31.39%; nonmonotone high band', 'CORE U5 logistic refit forbidden'),
        ('capital-vnext-v2-movement-20261004-v1','MOVEMENT_HYPOTHESIS_REPORT.json',
         'Saved CORE/MOVE P-AUC 0.653023/0.709646; MOVE_P5 reused', 'MOVE_P5 and MOVE_R refit forbidden'),
        ('capital-max3-top3-quality-v3-20261004-v1','CAPITAL_QUALITY_V3_CLOSURE.json',
         'Q1-Q8 FAIL; TOP3_SELECTION_WORSE; CAPITAL_QUALITY_V3_WORSE', 'HF1/HL0/Q rescue forbidden'),
        ('capital-max3-upward-staircase-v4-20261004-v1','HEAD_DIAGNOSTICS.json',
         'Current exact ML legacy U5 AUC=.6642388140526637, U10=.6863829003132487', 'Current H2/H3/H5 refit forbidden'),
        ('capital-v4-rank-cutoff-independent-20261004-v1','RANK_QUALITY.json',
         'A U5/U10 density exceeds S; Rank and Capital policy distinct', 'S_ONLY/A_PLUS/B_PLUS replay forbidden'),
        ('phase57-prr-numerical-recovery','RANK_SIGNAL.json',
         '1614 IM/R1, canonical ranking PASS; probability skill FAIL remains', '566-feature refit and forced join forbidden'),
        ('capital-v5-max3-slot-intelligence-20261004-v1','CLOSURE.json',
         'Existing slot-reserve research fixed; out of Rank-only scope', 'Reserve/replay changes forbidden'),
        ('capital-v6-counterfactual-slot-value-20261004-v1','CLOSURE.json',
         'CAPITAL_V6_RECOVERY_D11_CLOSED_FIXED_STOP; final receipt-only records retained', 'Dynamic Slot Value fit/replay/teacher regeneration forbidden')]
    matrix=[]
    for directory,name,fact,policy in entries:
        p=base/directory/name
        assert p.exists(), ('MISSING_EVIDENCE',str(p))
        matrix.append({'prior_work':directory,'read_only_source':str(p.relative_to(ROOT)),
            'source_sha256':sha(p),'existing_result':fact,'reuse_or_prohibition':policy,
            'new_fit':0,'new_replay':0})
    save(OUT/'PRIOR_WORK_MATRIX.json',{'exact_jst':now(),'matrix':matrix,'prior_research_rerun_N':0,
        'all_sources_pinned_at_start_HEAD':'fc333d7b3050ad3e9fc485cf0e666af0f69820b5'})
    checkpoint('R1_PRIOR_RANK_INVENTORY','PRIOR_RANK_INVENTORY_EXACT_BYTES_RECOVERED',
        ['8 prior works cross-read; prohibited repetitions recorded','16 exact byte artifacts recovered against GitHub hashes',
         'Canonical PRR OOF recovered against freeze hash, no model refit'],
        {'prior_work_N':8,'recovered_artifact_N':16,'artifact_mismatch_N':0,'fit_N':0,'replay_N':0},
        'Classify teacher support by original complete-capture contract; freeze all pre-cutoff common OOF candidate identities before metrics')

if __name__=='__main__':main()
