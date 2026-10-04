"""Required deterministic full rerun and execution boundary canaries only."""
from common import *
from replay import run_profile,day_replay
from copy import deepcopy
from decimal import Decimal as D
def main():
 cfg=json.loads((OUT/'POLICY_PRECOMMIT.json').read_text())
 for name,h in cfg['runtime_code_hashes'].items():assert sha(CODE/name)==h,('PRECOMMITTED_CODE_CHANGED',name)
 stream=rows(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz');books={r['entry_id']:r for r in rows(SRC/'bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz')};tables=json.loads((OUT/'ARRIVAL_TABLE.json').read_text())
 output=run_profile(PROFILE,3,stream,books,tables);saved=json.loads((PRIVATE/f'{PROFILE}_RESULT.json').read_text())
 rerun=output[0]|{'score_stream_sha256':sha(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz'),'avg_funded_per_session':output[0]['funded_N']/38}
 assert rerun==saved
 digests={}
 for label,data in zip(('DECISIONS','TRADES','CURVE','INTENTS'),output[1:]):
  assert data==rows(PRIVATE/f'{PROFILE}_{label}.jsonl.gz')
  bytes_=('\n'.join(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False) for r in data)+'\n').encode();compressed=gzip.compress(bytes_,mtime=0)
  digest=hashlib.sha256(compressed).hexdigest();assert digest==sha(PRIVATE/f'{PROFILE}_{label}.jsonl.gz');digests[label]=digest
 # Same-batch first candidate cannot afford one lot; no backfill of fourth.
 day='2000-01-01';candidates=[];synthetic_books={};t=570
 for i,price in enumerate(('60000','1000','1000','1000')):
  key=f'{day}|CANARY{i}';row=deepcopy(stream[0]);row.update(entry_id=key,session=day,symbol=f'CANARY{i}',entry_minute=t,entry_timestamp=day+'T09:30:00+09:00',raw_reference=price,ML=2.,capital_score=2.,rank='S',capacity_band='S',admission=True,block=1)
  candidates.append(row)
  market=[{'session':day,'minute':570,'O':price,'H':str(D(price)*D('1.1')),'L':price,'C':str(D(price)*D('1.1')),'Vo':'100','Va':'100000','lineage':{'synthetic_canary':True}}, {'session':day,'minute':920,'O':price,'H':price,'L':price,'C':price,'Vo':'100','Va':'100000','lineage':{'synthetic_canary':True}}]
  synthetic_books[key]={'session':day,'entry_actual_source':market[0],'capture_complete':True,'frozen_exit':{'sell_status':'NOT_FILLED'},'market':market,'limit_up_authority':None}
 synthetic=day_replay(3,day,candidates,synthetic_books,D(1000000),tables=tables);dec=synthetic[1];frames=synthetic[3]
 assert dec[0]['reason']=='CASH_OR_LOT_CONSTRAINED' and dec[3]['reason']=='MAX_POSITION_CAP'
 assert sum(d['reason']=='FUNDED' for d in dec)==2 and dec[3]['quantity']==0
 a=next(x for x in frames if x['minute']==570);b=next(x for x in frames if x['minute']==571);assert a['cash']==b['cash'] and a['equity']!=b['equity']
 before=next(x for x in frames if x['minute']==920);after=next(x for x in frames if x['minute']==921);assert D(after['cash'])>D(before['cash']) and after['concurrent']==0
 assert len({x['entry_id'] for x in synthetic[2]})==len(synthetic[2])
 save(OUT/'DETERMINISTIC_RERUN.json',{'JST':now(),'PASS':True,'full_canary_rerun':1,'all_decisions_trades_frames_intents_byte_identical':digests,'result_identity':True,'Primary_policy_replay_N':1,'Control_replay_N':0,'causal_day_canary_replays_before_primary':5,'synthetic_day_canary_replays_after_primary':1,'synthetic_no_forced_backfill':True,'synthetic_MTM_changes_equity_not_cash':True,'synthetic_only_valid_EOD_fill_releases_cash':True,'duplicate_sell0':True,'threshold_changes':0})
 print(json.dumps({'full_deterministic_identity':'PASS','no_backfill_MTM_cash_release':'PASS'}))
if __name__=='__main__':main()
