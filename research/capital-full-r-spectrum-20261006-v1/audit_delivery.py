"""Supplement only final filled-lot decomposition and delivery/CSV bindings."""
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from zoneinfo import ZoneInfo
import csv,gzip,hashlib,json
REPO=Path(__file__).resolve().parents[2];ROOT=REPO.parent
OUT=REPO/'docs/evidence/capital-full-r-spectrum-20261006-v1';PRIVATE=ROOT/'capital_r_spectrum_private'
def read(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(s) for s in gzip.open(p,'rt') if s.strip()]
def main():
    original=rows(ROOT/'capital_v51_private/evaluation-only/R_LABELS.jsonl.gz');lm={r['entry_id']:r for r in original}
    joined=rows(PRIVATE/'evaluation-only/ENTRY_JOINED_ANATOMY.jsonl.gz');tranches=read(OUT/'ACTUAL_LOT_TRANCHE_FLOW.json');checks=0
    for s in tranches['rows']:
        rr=[r for r in joined if r['actual_funded_trade'] is not None and r['events'][s['label']]]
        base_buy=sum((Decimal(lm[r['entry_id']]['buy_debit']) for r in rr),Decimal(0));base_pnl=sum((Decimal(lm[r['entry_id']]['sell_credit'])-Decimal(lm[r['entry_id']]['buy_debit']) for r in rr),Decimal(0))
        total_buy=sum((Decimal(r['actual_funded_trade']['debit']) for r in rr),Decimal(0));total_pnl=sum((Decimal(r['actual_funded_trade']['pnl']) for r in rr),Decimal(0))
        assert Decimal(s['actual_first100_debit_jpy'])==base_buy and Decimal(s['actual_beyond100_debit_jpy'])==total_buy-base_buy
        assert Decimal(s['actual_first100_pnl_jpy'])==base_pnl and Decimal(s['actual_beyond100_pnl_jpy'])==total_pnl-base_pnl
        assert s['actual_first100_shares']==100*len(rr) and s['actual_beyond100_shares']==sum(r['actual_funded_trade']['quantity']-100 for r in rr)
        assert s['native_water_fill_shares']==sum(r['native_decision']['quantity']-r['native_decision']['first_pass_quantity'] for r in rr)
        checks+=4
    # CSV publication cannot change numeric census or pooled raw directions.
    census=read(OUT/'R_FULL_CENSUS.json')['populations'];cc=list(csv.DictReader((OUT/'R_FULL_CENSUS.csv').open()))
    for c in cc:
        z=census[c['population']]
        source=z['unknown_mask'] if c['bucket_pp_lower']=='UNKNOWN' else next(b for b in z['buckets'] if b['bucket_pp_lower']==int(c['bucket_pp_lower']))
        for key in ['candidate_N','eligible_N','rank_pass_N','funded_N','funded_shares','missed_N']:
            assert int(c[key])==source[key];checks+=1
    score=read(OUT/'SCORE_R_SPECTRUM.json');curves=list(csv.DictReader((OUT/'SCORE_R_SPECTRUM.csv').open()))
    assert len(curves)==len(score['pooled'])
    for c,s in zip(curves,score['pooled']):
        assert c['population']==s['population'] and c['head']==s['head'] and c['label']==s['label']
        assert int(c['N'])==s['N'] and int(c['positive_N'])==s['positive_N']
        assert (float(c['raw_direction_AUROC']) if c['raw_direction_AUROC'] else None)==s['raw_direction_AUROC'];checks+=3
    # Original engine and prior evidence are still byte-identical.
    old=REPO/'docs/evidence/capital-v51-reset20-r5r10-20261006-v1';binding=read(OUT/'START_AND_SOURCE_BINDING.json')
    for s in binding['prior_authority_actual_GET']:
        assert hashlib.sha256((old/s['name']).read_bytes()).hexdigest()==s['sha256'];checks+=1
    authority=read(old/'V51_POLICY_PRECOMMIT.json')
    for name,s in authority['native_code_hashes'].items():
        assert hashlib.sha256((REPO/'research/capital-v5-max3-slot-intelligence-20261004-v1'/name).read_bytes()).hexdigest()==s;checks+=1
    contract=read(OUT/'R_SPECTRUM_CONTRACT.json');meta=read(PRIVATE/'DERIVATION_COMPLETE.json')
    assert meta['derived_batch_N']==1 and contract['evaluation_only'];checks+=1
    result={'schema':'ARK_FINAL_DELIVERY_SUPPLEMENTAL_AUDIT_V1','exact_jst':datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),
         'pass':True,'mismatch_N':0,'check_N':checks,'scope':'Only newly added filled-lot tranche decomposition, CSV publication and freeze hashes; original82100-item audit not rerun','audit_invocations':1,'new_Capital_replays':0,'R_market_EXIT_rematerializations':0}
    (OUT/'DELIVERY_AUDIT.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
