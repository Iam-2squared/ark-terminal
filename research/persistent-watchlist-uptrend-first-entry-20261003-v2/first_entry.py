"""Score-only threshold machine; future evaluator is a separate subsequent stage."""
import collections
from common import *
def generate():
 grid=list(lines(HERE/'PERSISTENT_GRID.jsonl.gz'));ws=[w for w in lines(HERE/'WATCH_RECORDS.jsonl.gz') if w['canonical']];intents=[];counts={}
 for family in ('P0','P1'):
  z=np.load(HERE/'PRIVATE_INPUTS'/f'oof_{family}.npz');by=collections.defaultdict(list)
  for j,i in enumerate(z['row_indices']):by[grid[i]['watch_key']].append(j)
  for pi,policy in enumerate(POLICIES):
   evaluated=0
   for w in ws:
    selected=None;decision_count=0;past=[]
    for j in by[w['watch_key']]:
     i=int(z['row_indices'][j]);r=grid[i];assert r['feature_max_timestamp']<=r['intent_timestamp'];decision_count+=1;score=float(z['score'][j]);threshold=float(z['thresholds'][j,pi])
     past.append([r['intent_minute'],score,threshold])
     if score>=threshold:
      selected={'row_index':i,'row_id':r['row_id'],'intent_minute':r['intent_minute'],'intent_timestamp':r['intent_timestamp'],'fold':int(z['fold'][j]),'score':score,'threshold':threshold};break
    evaluated+=decision_count
    intents.append({'watch_key':w['watch_key'],'session':w['session'],'symbol':w['symbol'],'first_selector_event':w['first_selector_event'],'selector_minute':w['selector_minute'],'selector_price':w['selector_price'],'family':family,'policy':policy,'first_intent':selected,'scoring_decisions':decision_count,'threshold_trace_sha256':hashlib.sha256(json.dumps(past,separators=(',',':')).encode()).hexdigest(),'decision_after_first_entry':0,'second_intent':0,'EXIT_calls':0,'reentry_calls':0})
   counts[family+'_'+policy]=evaluated
 write_lines(HERE/'FIRST_INTENTS_PRIVATE.jsonl.gz',intents);write(HERE/'FIRST_ENTRY_MACHINE_RECEIPT.json',{'saved_at_jst':now(),'watches_per_family_policy':len(ws),'policies':list(POLICIES),'families':['P0','P1'],'score_decisions_by_policy':counts,'first_intent_records':len(intents),'input_channels':['causal grid metadata','OOF uptrend scores','frozen training thresholds'],'evaluator_read_during_threshold_decision':False,'EXIT_calls':0,'reentry_calls':0,'second_entry':0,'old_30m_limit':False,'safety':SAFETY})
def fill_and_evaluate():
 # Decision records are sealed before future raw prices are consulted here.
 from teacher import next_fill,future_metrics
 raw=read(INPUT/'raw_paths_selected.json.gz');intents=list(lines(HERE/'FIRST_INTENTS_PRIVATE.jsonl.gz'));by=collections.defaultdict(list);counts=collections.Counter()
 for r in intents:
  a=clean_array(raw[r['watch_key']]['today']);intent=r['first_intent'];f=next_fill(r['session'],a,intent['intent_minute']) if intent else None
  if not intent:r.update(entry_status='NO_ENTRY_NO_THRESHOLD_CROSS',fill_minute=None,fill_price=None)
  elif f is None:r.update(entry_status='NO_ENTRY_NO_NEXT_REGULAR_OPEN',fill_minute=None,fill_price=None)
  else:
   r.update(entry_status='FIRST_ENTRY',fill_minute=f[0],fill_price=f[1],fill_timestamp=stamp(r['session'],f[0]),selector_to_entry_active_delay=active_elapsed(r['session'],r['selector_minute'],f[0]),selector_to_intent_active_delay=active_elapsed(r['session'],r['selector_minute'],intent['intent_minute']),intent_to_fill_active_delay=active_elapsed(r['session'],intent['intent_minute'],f[0]),first_entry_count=1)
   r.update(future_metrics(r['session'],a,*f))
  counts[r['family']+'_'+r['policy']+'_'+r['entry_status']]+=1;by[r['policy']].append(r)
 for p,rs in by.items():write_lines(HERE/f'FIRST_ENTRY_{p}.jsonl.gz',rs)
 receipt=read(HERE/'FIRST_ENTRY_MACHINE_RECEIPT.json');receipt.update(fill_and_evaluation_saved_at_jst=now(),counts=dict(counts),FIRST_ENTRY_after_fill_stop=True);write(HERE/'FIRST_ENTRY_MACHINE_RECEIPT.json',receipt)
if __name__=='__main__':generate();fill_and_evaluate()
