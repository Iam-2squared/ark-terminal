"""Materialize fixed46 causal numeric fields; teachers stay in a separate file."""
from collections import Counter
from decimal import Decimal
import json
from checkpoint import ROOT,OUT,PRIVATE,save,sha
from io_data import rows,gzwrite,books,core_runtime,calendar,history
from movement import project,raw_prefix,activity,complete,MOVEMENT_KEYS
from allocation import liquidity
from execution import frozen_execution,eod_source,BUY

def realized_teacher(core,book):
 if core['entry_minute']>=920:
  return {'label_realized_positive':None,'realized_net_return':None,'execution_status':'ENTRY_AFTER_CAPITAL_CUTOFF'}
 if not book['capture_complete'] or not book.get('entry_actual_source'):
  return {'label_realized_positive':None,'realized_net_return':None,'execution_status':'SOURCE_LINEAGE_BLOCKED'}
 source=frozen_execution(book)
 if source is None:source=eod_source(book['market'],core['session'])
 if source is None or source.get('blocked'):
  return {'label_realized_positive':None,'realized_net_return':None,
   'execution_status':source.get('blocked') if source else 'EOD_UNEXECUTED_FAIL_CLOSED'}
 assert source['release_minute']>core['entry_minute']
 buy=Decimal(core['raw_reference'])*BUY;sell=Decimal(source['price']);net=sell/buy-1
 return {'label_realized_positive':int(net>0),'realized_net_return':float(net),'execution_status':'COMPLETE',
  'exit_kind':source['kind'],'source_minute':source['source_minute'],'release_minute':source['release_minute'],
  'buy_effective':str(buy),'sell_effective':str(sell),'source_lineage':source['lineage']}

def main():
 assert (OUT/'DESIGN_PRECOMMIT.json').exists() and (OUT/'FEATURE_MANIFEST.json').exists()
 hist,receipt=history();cal=calendar();bb=books();cores=core_runtime()
 oldteacher={r['entry_id']:r for r in rows(ROOT.parent/'bigwinner_private/TEACHERS_EVALUATION_V2.jsonl.gz')}
 oldhist={}
 import gzip
 for name in ('bigwinner_source','bigwinner_supplement'):
  rr=json.load(gzip.open(ROOT.parent/f'work_inputs/{name}/SAVED_SOURCE_PRIVATE.json.gz','rt'))
  oldhist.update({(r['session'],r['symbol']):r for r in rr})
 conflicts=0
 for key,r in hist.items():
  if complete(r) and not r['prefixes']:
   assert int(r['active_minute_bitmap_hex'],16)==0
   clocks=json.loads((ROOT/'research/capital-vnext-v2-movement-20261004-v1/SOURCE_RECOVERY_SCOPE.json').read_text())['entry_clock_by_symbol_hash']
   import hashlib
   r['prefixes']={str(t):raw_prefix([],t) for t in clocks[hashlib.sha256(r['symbol'].encode()).hexdigest()]}
  old=oldhist.get(key)
  if old and old.get('daily') and r.get('daily'):
   old_va,new_va=old['daily']['Va'],r['daily']['Va']
   conflicts+=(old_va!=new_va) if old_va is None or new_va is None else Decimal(str(old_va))!=Decimal(str(new_va))
   conflicts+=len(old['active_windows'])!=activity(r['active_minute_bitmap_hex'])['active_5m_N']
 assert conflicts==0,'RECOVERED_SOURCE_V1_VALUE_COVERAGE_CONFLICT'
 runtime=[];teachers=[];missing=Counter();liquids=Counter();rstatuses=Counter()
 for core in cores:
  movement,provenance=project(core,hist,cal,bb[core['entry_id']]['market'])
  liq=liquidity(core,cal,hist)
  rr={**core,'numeric':{**core['numeric'],**movement},'liquidity':liq,'movement_provenance':provenance}
  assert len(rr['numeric'])==46 and not any(k in rr for k in ('label_realized_positive','label_bigwinner5','frozen_exit'))
  runtime.append(rr);liquids[liq['reason']]+=1
  for k,v in movement.items():missing[k]+=v is None
  teacher={**oldteacher[core['entry_id']],**realized_teacher(core,bb[core['entry_id']]),
   'scope':'TRAINING/EVALUATION ONLY; labels and future execution are never runtime fields.'}
  teachers.append(teacher);rstatuses[teacher['execution_status']]+=1
 gzwrite(PRIVATE/'RUNTIME_CAUSAL.jsonl.gz',runtime);gzwrite(PRIVATE/'TEACHERS_EVALUATION.jsonl.gz',teachers)
 save(PRIVATE/'SOURCE_MANIFEST_RECOVERED.json',{'initial':json.loads((PRIVATE/'SOURCE_MANIFEST.json').read_text()),
  'recovery_receipt_hash':sha(ROOT.parent/'work_inputs/movement_v2_source/MOVEMENT_SOURCE_RECEIPT.json'),
  'recovery_scope_hash':receipt['scope_sha256'],'movement_shards':receipt['shards'],
  'runtime_hash':sha(PRIVATE/'RUNTIME_CAUSAL.jsonl.gz'),'teacher_hash':sha(PRIVATE/'TEACHERS_EVALUATION.jsonl.gz')})
 report={'candidate_N':len(runtime),'session_N':58,'core_numeric_N':27,'movement_numeric_N':19,'categorical_N':7,
  'Movement_missing_N':dict(missing),'extreme_liquidity_status':dict(liquids),
  'realized_teacher_status':dict(rstatuses),'P_teacher_positive_N':sum(t['label_bigwinner5']==1 for t in teachers),
  'R_teacher_positive_N':sum(t['label_realized_positive']==1 for t in teachers),
  'R_unknown_N':sum(t['label_realized_positive'] is None for t in teachers),'source_value_coverage_conflicts':0,
  'runtime_sha256':sha(PRIVATE/'RUNTIME_CAUSAL.jsonl.gz'),'teacher_sha256':sha(PRIVATE/'TEACHERS_EVALUATION.jsonl.gz'),
  'source_receipt_sha256':sha(ROOT.parent/'work_inputs/movement_v2_source/MOVEMENT_SOURCE_RECEIPT.json'),
  'protected_opened':0,'future_labels_in_runtime':False,'fit_count':0,'productionReady':False}
 save(OUT/'FEATURE_MATERIALIZATION_RESULT.json',report)
 print(json.dumps(report))

if __name__=='__main__':main()
