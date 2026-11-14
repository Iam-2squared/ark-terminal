"""Immutable EXIT schedule compiled from forward causal prefixes; after funding only."""
from io_utils import *
import sys,importlib.util
sys.path.insert(0,str(NATIVE))
import execution as canonical
spec=importlib.util.spec_from_file_location('s4_corrected_numeric_adapter',SHARP/'implementation/numeric_adapter.py')
numeric=importlib.util.module_from_spec(spec);spec.loader.exec_module(numeric)

def route(buy,control,frames):
 for r in frames:
  t=r['checkpoint_minute']
  if t>=control:return {'action':'DELEGATE_CONTROL','intent_minute':control,'reason':'CONTROL_FIRST_OR_SAME_CHECKPOINT'}
  if r['evidence_gap']:return {'action':'EVIDENCE_GAP','intent_minute':None,'block_minute':t,'reason':'EVIDENCE_GAP_BEFORE_CONTROL'}
  if t>buy and r['usable'] and r['Primary']=='SHARP_DROP':return {'action':'SD_FIRST','intent_minute':t,'reason':'SHARP_DROP_FIRST_OBSERVED'}
 return {'action':'DELEGATE_CONTROL','intent_minute':control,'reason':'NO_PRIOR_USABLE_SHARP_DROP'}

def compile_plan(book,buy,frames,control=None,cut_market=True):
 native=book['frozen_exit']['exit_intent']
 control=control if control is not None else min(native['minute'],920) if native else 920
 choice=route(buy,control,frames)
 cf=canonical.frozen_execution(book)
 csource=cf if cf is not None else canonical.eod_source(book['market'],book['session'])
 terminal=csource.get('source_minute') if csource and csource.get('price') else 930
 if choice['action']=='SD_FIRST':
  # Inherit S4's exact bounded canonical source set, including locked terminal rule.
  market=[r for r in book['market'] if r.get('session')==book['session'] and r['minute']<=terminal] if cut_market else book['market']
  fill=numeric.resolve_fill({'session':book['session'],'buy_fill_minute':buy,'market':market},choice['intent_minute'])
  if fill['status']=='FILLED':
   raw=F(int(fill['raw_price_numerator']),int(fill['raw_price_denominator']))
   effective=F(int(fill['effective_price_numerator']),int(fill['effective_price_denominator']))
   with localcontext() as c:c.prec=60;price=str(D(effective.numerator)/D(effective.denominator))
   source={'kind':'SHARP_DROP_FIRST_OBSERVED_EXIT_V0','source_minute':fill['source_minute'],'release_minute':fill['source_available_minute'],'price':price,'lineage':fill['source_lineage'],'overlay_intent_minute':choice['intent_minute'],'raw_price':fmt(raw),'locked_terminal':fill['closing_fallback_for_latched_intent']}
  else:source=None
  choice.update(source=source,fill=fill,canonical_source_cutoff_minute=terminal)
 else:choice['source']=cf
 choice.update(control_intent_minute=control,checkpoint_N=sum(r['checkpoint_minute']<=choice.get('intent_minute',control) for r in frames) if choice.get('intent_minute') is not None else sum(r['checkpoint_minute']<=choice['block_minute'] for r in frames),usable_checkpoint_N=sum(r['usable'] and r['checkpoint_minute']<=choice.get('intent_minute',control) for r in frames) if choice.get('intent_minute') is not None else 0)
 return choice
