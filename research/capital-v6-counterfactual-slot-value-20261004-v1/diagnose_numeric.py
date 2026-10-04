"""Isolated original failed teacher solve, no fits or policy changes."""
from common import *
from teachers import execution_row
from staircase import candidate_order
import teacher_oracle as original
from decimal import Decimal as D
def main():
 block=7;key='682973993eaf10ee6f745ebad1eeff97e9e06fa2a67df25a18345227cdf30d2b';state=next(s for s in rows(PRIVATE/'TRAINING_STATES_BLOCK_07.jsonl.gz') if s['state_key']==key)
 runtime={r['entry_id']:r for r in rows(SRC/'capital_quality_v3_private/CORE_RUNTIME_CAUSAL.jsonl.gz')};stream=[dict(r,raw_reference=runtime[r['entry_id']]['raw_reference'],entry_timestamp=runtime[r['entry_id']]['entry_timestamp']) for r in rows(V5PRIVATE/'TRAINING_ONLY_SCORED_ARRIVALS.jsonl.gz') if r['block']==block];byid={r['entry_id']:r for r in stream};cur=byid[state['entry_id']]
 books={r['entry_id']:r for r in rows(SRC/'bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz')};labels={r['entry_id']:r for r in rows(SRC/'capital_v2_private/TEACHERS_EVALUATION.jsonl.gz')}
 remaining=[r for r in stream if r['session']==state['session'] and r['admission'] and r['entry_minute']<920 and (r['entry_id'] in state['pending_ids'] or (r['entry_minute'],candidate_order(r))>=(cur['entry_minute'],candidate_order(cur)))];a=[z for r in remaining if (z:=execution_row(r,books,labels)) is not None];h=[]
 for k,p in state['held'].items():
  z=execution_row(byid[k],books,labels);h.append({'entry_id':k,'release_minute':z['release_minute'],'credit':str(D(z['credit'])*(p['quantity']//100))})
 results=[];method=original.milp
 def capture(*args,**kwargs):
  r=method(*args,**kwargs);results.append({'status':int(r.status),'success':bool(r.success),'mip_gap':float(r.mip_gap),'fun':float(r.fun),'mip_dual_bound':float(r.mip_dual_bound),'nodes':int(r.mip_node_count),'message':r.message,'x':r.x.tolist()});return r
 original.milp=capture
 try:original.solve(state,a,h,labels,True);error=None
 except AssertionError as e:error=repr(e)
 record={'exact_jst':now(),'state':state,'candidate_physical_continuation':a,'held_release_obligations':h,'solver_results':results,'original_assertion':error,'Oracle_constraints_changed':False,'teacher_action_changed':False,'slot_fit':0,'main_replay':0}
 save(PRIVATE/'BLOCK07_NUMERIC_ISOLATION.json',record)
 print(json.dumps({k:record[k] for k in ['exact_jst','original_assertion']}|{'results':[{k:v for k,v in r.items() if k!='x'} for r in results]}))
if __name__=='__main__':main()
