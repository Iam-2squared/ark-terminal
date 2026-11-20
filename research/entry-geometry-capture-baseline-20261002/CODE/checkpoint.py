#!/usr/bin/env python3
"""Stamp a checkpoint immediately before publication; result commit is GitHub authority."""
import argparse,json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
P=Path(__file__).resolve().parents[1]
BUDGET=dict.fromkeys(['new_entry_model_fits','state_model_fits','exit_model_fits','threshold_searches','new_policy_replays','provider_requests','Protected_open','Holdout_open','Validation_new_open','OOS_open','Prospective_open','orders','paper_trades','live_trades','main_merges','bootstrap'],0)
SAFETY=dict.fromkeys(['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted'],False)
def stamp(stage,name,basis,status,done,evidence,blockers=None):
    jst=datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()
    obj=dict(checkpoint=stage,saved_at_jst=jst,basis_head=basis,
        previous_checkpoint_result_head=basis,current_status=status,
        completed_this_checkpoint=done,key_evidence=evidence,blockers=blockers or [],
        current_direction='Saved-evidence descriptive Entry Geometry; V6 closed STATE_R2_SIGNAL_NOT_REPLICATED; Hybrid next-spec only after integrity PASS',
        next_step={'C1':'C2 metric freeze before Geometry aggregates','C2':'C3 saved evidence join','C3':'C4 descriptive aggregation and graphs','C4':'C5 independent arithmetic audit from originals','C5':'C6 interpretation and PROPOSED_NOT_AUTHORIZED next-spec','C6':'Stop before any Hybrid fit; separate finite precommit required'}[stage],
        frozen_boundaries=['Selector / State9 RC2 / Path / targets unchanged','No new Entry decisions / fit / Replay / provider','No new partition exposure','No main merge / force push / orders','Fixed requested bucket edges','R2 probabilities/ranks not promoted'],
        exposure_and_budget=BUDGET,safety=SAFETY,
        result_head='GitHub commit itself is authoritative; no future SHA predicted')
    d=P/'CHECKPOINTS';d.mkdir(exist_ok=True)
    (d/(name+'.json')).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
    md='# 💾 '+name+'\n\n'+'\n\n'.join('## '+k+'\n\n'+('```json\n'+json.dumps(v,ensure_ascii=False,indent=2)+'\n```' if isinstance(v,(dict,list)) else str(v)) for k,v in obj.items())+'\n'
    (d/(name+'.md')).write_text(md)
    print(json.dumps({'checkpoint':stage,'saved_at_jst':jst,'basis_head':basis,'status':status}))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('config');args=ap.parse_args()
    stamp(**json.loads(Path(args.config).read_text()))
