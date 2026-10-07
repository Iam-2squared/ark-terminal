"""Generate a local research adapter with explicit minimal native event-loop substitutions."""
from io_utils import *
import ast

def run():
 src=(NATIVE/'replay.py').read_text();tree=ast.parse(src)
 code=ast.get_source_segment(src,next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='day_replay'))
 changes=[]
 def replace(old,new):
  nonlocal code
  assert code.count(old)==1,(old,code.count(old))
  code=code.replace(old,new);changes.append({'old':old,'new':new})
 replace('tables=None):','tables=None,exit_plans=None):')
 replace(" assert n==3,'MAX3_ONLY_RESEARCH_POLICY'"," if exit_plans is None:return native_day_replay(n,day,candidates,books,starting_cash,primary_chain,profile,tables)\n assert n==3,'MAX3_ONLY_RESEARCH_POLICY'")
 replace("  batch=sorted(events.get(t,[]),key=candidate_order)","  for key,p in sorted(positions.items()):\n   plan=p['exit_plan']\n   if plan['action']=='EVIDENCE_GAP' and t==plan['block_minute']:\n    blockers.append({'entry_id':key,'minute':t,'reason':plan['reason']})\n   if plan['action']=='SD_FIRST' and t==plan['intent_minute']:\n    p['overlay_pending']=True;p['intent_issued']=True\n    intents.append({'entry_id':key,'session':day,'minute':t,'side':'SELL','quantity':p['quantity'],'reason':'SHARP_DROP_FIRST_OBSERVED','transmitted':False,'latched':True})\n  if any(b['reason']=='EVIDENCE_GAP_BEFORE_CONTROL' and b['minute']==t for b in blockers):break\n  batch=sorted(events.get(t,[]),key=candidate_order)")
 replace("    prior=frozen_execution(book)","    plan=exit_plans[key]\n    positions[key]['exit_plan']=plan\n    positions[key]['overlay_pending']=False\n    prior=plan.get('source')")
 replace("    it=eod_intent(p);assert it is not None;p['intent_issued']=True","    if p.get('overlay_pending'):continue\n    it=eod_intent(p);assert it is not None;p['intent_issued']=True")
 replace("  eq=equity();assert cash>=0 and eq>0","  eq=equity();assert cash>=0 and eq>0\n  if any(b['reason']=='MTM_SOURCE_LINEAGE_BLOCKED' for b in blockers):break")
 replace(" valid=not blockers and not positions"," snapshot={'window_arm_event_cursor':{'session':day,'minute':t},'cash':str(cash),'holdings':{k:{f:str(v) if isinstance(v,D) else v for f,v in p.items() if f not in ('mark_updates','exit_plan')} for k,p in positions.items()},'pending_SELL':{k:p['exit_plan'] for k,p in positions.items()},'remaining_fill_schedule':{str(tm):ss for tm,ss in fills.items()}}\n valid=not blockers and not positions")
 replace("  'primary_chain':primary_chain,'blockers':blockers,'open_obligations':list(positions),","  'primary_chain':primary_chain,'blockers':blockers,'open_obligations':list(positions),'resume_snapshot':snapshot,")
 header='''"""Derived event-loop adapter; all funding functions imported unchanged from S2."""\nfrom io_utils import *\nimport sys\nsys.path.insert(0,str(NATIVE))\nfrom collections import defaultdict\nfrom execution import BUY,SELL,valid_market,eod_intent,eod_source,limit_up_confirmed\nfrom allocation import allocation,band\nfrom staircase import candidate_order\nfrom slot_policy import gate\nfrom replay import day_replay as native_day_replay\nPROFILE='CAPITAL_MAX3_SLOT_RESERVE_V1'\n'''
 atomic(ROOT/'portfolio.py',(header+'\n'+code+'\n').encode())
 save(PUB/'PORTFOLIO_ADAPTER_PATCH.json',{'native_replay_pin':pin(NATIVE/'replay.py'),'new_adapter_pin':pin(ROOT/'portfolio.py'),'substitutions':changes,'allocator_imported_byte_identical':True,'overlay_OFF_delegates_native_day_function':True,'State_trace_compile_is_outside_buy_allocator':True,'gap_detected_only_for_funded_positions':True})
 print('Portfolio adapter generated; native code unchanged')
if __name__=='__main__':run()
