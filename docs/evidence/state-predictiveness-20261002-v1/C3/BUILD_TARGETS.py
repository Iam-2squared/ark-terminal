"""Stage D: targets only after immutable causal feature files are fixed."""
from pathlib import Path
from decimal import Decimal,localcontext,Context,ROUND_HALF_EVEN
from fractions import Fraction
from collections import Counter
import datetime,hashlib,json,sys
R=Path(__file__).resolve().parent
DATA=R/'RECEIVED_DEVELOPMENT'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(n,x):
 p=R/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def price_target(rows,index,h,base=None):
 row=rows[index];source=row['audit_source'];base=index if base is None else base
 out={'available':False,'unavailable_reason':None,'future_key':None,'label_end':None,'horizon':h,'label_start':row['bar_end']}
 if not source['raw_present'] or source['numeric_status']!='ACCEPTED':out['unavailable_reason']='START_UNAVAILABLE';return out
 if row['tradable_index'] is None:out['unavailable_reason']='START_AUCTION';return out
 lookup={x['tradable_index']:i for i,x in enumerate(rows) if x['tradable_index'] is not None}
 target_index=lookup.get(row['tradable_index']+h)
 if target_index is None:out['unavailable_reason']='EXACT_HORIZON_OUTSIDE_SESSION';return out
 future=rows[target_index];out.update(future_key=future['row_key'],label_end=future['bar_end'])
 if not future['audit_source']['raw_present'] or future['audit_source']['numeric_status']!='ACCEPTED':out['unavailable_reason']='EXACT_HORIZON_UNAVAILABLE';return out
 segment=row['causal_segment_id']
 for k in range(index,target_index+1):
  x=rows[k]
  if x['causal_segment_id']!=segment:out['unavailable_reason']='CAUSAL_SEGMENT_BREAK';return out
  if not x['audit_source']['raw_present'] or x['audit_source']['numeric_status']!='ACCEPTED':out['unavailable_reason']='INTERVENING_UNKNOWN_OR_REJECTED';return out
  if x['audit_source']['auction']!='CONTINUOUS':out['unavailable_reason']='AUCTION_OR_OPENING_BOUNDARY';return out
 a=Decimal(source['Close_JPY']);b=Decimal(future['audit_source']['Close_JPY']);u=Decimal(source['U'])
 exact=(Fraction(source['Close_JPY'])-Fraction(future['audit_source']['Close_JPY']))/Fraction(source['U'])
 exact=-exact
 with localcontext(Context(prec=80,rounding=ROUND_HALF_EVEN,Emin=-999999,Emax=999999)):
  y=(b-a)/u;delta=Decimal(future['audit_source']['x_C'])-Decimal(source['x_C'])
 out.update(available=True,unavailable_reason=None,y_token=format(y,'f'),y_exact_rational=str(exact),direction=0 if b==a else 1 if b>a else -1,delta_x_token=format(delta,'f'),Close_start_token=source['Close_JPY'],Close_future_token=future['audit_source']['Close_JPY'],U_token=source['U'],x_start_token=source['x_C'],x_future_token=future['audit_source']['x_C'],label_segment=segment,start_source_pointer=row['source_pointer'],future_source_pointer=future['source_pointer'],intervening_slots_N=target_index-index+1)
 return out
def structural(rows,i):
 row=rows[i];source=row['audit_source'];ti=row['tradable_index'];out={'next_primary_available':False,'transition_window_available':False,'transition_within30':None,'next_transition_at':None,'time_to_next_transition':None,'censored_at30':False}
 if ti is None or not source['observed']:out['reason']='CURRENT_NOT_OBSERVED_OR_AUCTION';return out
 lookup={r['tradable_index']:j for j,r in enumerate(rows) if r['tradable_index'] is not None};j=lookup.get(ti+1)
 if j is not None:
  r=rows[j]
  if j==i+1 and r['audit_source']['observed'] and r['causal_segment_id']==row['causal_segment_id'] and r['audit_source']['auction']=='CONTINUOUS':
   p=r['audit_source']['formal_primary'];out.update(next_primary_available=True,next_primary=p,next_primary_key=r['row_key'],next_primary_label_end=r['bar_end'],continuation_or_change='CONTINUATION' if p==source['formal_primary'] else 'PRIMARY_CHANGE')
 full=price_target(rows,i,30)
 if not full['available']:out['reason']='30_WINDOW_'+str(full['unavailable_reason']);return out
 end=lookup[ti+30];out.update(transition_window_available=True,transition_within30=0,transition_label_end=rows[end]['bar_end'],censored_at30=True)
 for r in rows[i+1:end+1]:
  trs=[e for e in r['audit_source']['events'] if e['event_type']=='TRANSITION']
  if not trs:continue
  assert len(trs)==1 and r['causal_segment_id']==row['causal_segment_id']
  tr=trs[0];a=source['local_direction'];b=r['audit_source']['local_direction'];relation=None if a in (None,0) or b in (None,0) else 'REVERSAL' if a==-b else 'CONTINUATION'
  out.update(transition_within30=1,next_transition_from=tr['from_primary_or_null'],next_transition_to=tr['to_primary_or_null'],next_transition_at=r['bar_end'],time_to_next_transition=r['tradable_index']-ti,direction_relation=relation,censored_at30=False)
  break
 return out
def execute():
 pre=json.loads((R/'PREDICTIVENESS_PRECOMMIT.json').read_text())
 for n,h in pre['hashes'].items():assert digest(R/n)==h,'PRECOMMIT_CHANGED'
 manifest=json.loads((DATA/'DATASET_MANIFEST.json').read_text());fixed=json.loads((DATA/'C2_DATA_FEATURES_FIXATION.json').read_text())
 assert manifest['features_completed_before_label_builder'] and fixed['label_rows_generated']==0
 assert digest(DATA/'DATASET_MANIFEST.json')==fixed['dataset_manifest_SHA256']
 assert manifest['contract_SHA256']==pre['hashes']['PREDICTIVENESS_CONTRACT_V1.md']
 counts=Counter();features_N=0;label_records_N=0;keyset=set();files=[];structural_N=Counter();all_dates=[]
 for p in manifest['pairs']:
  f=DATA/'FEATURES'/f"{p['pair_id']}.jsonl";assert digest(f)==p['feature_SHA256']
  rows=[json.loads(l) for l in f.read_text().splitlines()];assert len(rows)==p['scheduled_endpoints_N']
  assert all(rows[k]['scheduled_t']<rows[k+1]['scheduled_t'] for k in range(len(rows)-1))
  t=R/'LABELS'/f"{p['pair_id']}.jsonl";t.parent.mkdir(exist_ok=True)
  with t.open('w') as writer:
   for i,row in enumerate(rows):
    assert row['row_key'] not in keyset,'DUPLICATE_KEY';keyset.add(row['row_key']);features_N+=1
    assert row['feature_created_before_target'] and row['feature_max_timestamp']<=row['bar_end']
    targets={str(h):price_target(rows,i,h) for h in [5,15,30]}
    shift={}
    ti=row['tradable_index'];lookup={x['tradable_index']:j for j,x in enumerate(rows) if x['tradable_index'] is not None}
    si=None if ti is None else lookup.get(ti+60)
    for h in [5,15,30]:
     if si is None:sh={'available':False,'unavailable_reason':'SHIFT_START_OUTSIDE_SESSION','horizon':h}
     else:
      sh=price_target(rows,si,h)
      # Shift control must also preserve the full t..shifted-horizon causal window.
      guard=price_target(rows,i,60+h)
      if not guard['available']:sh={'available':False,'unavailable_reason':'SHIFT_'+str(guard['unavailable_reason']),'horizon':h}
     shift[str(h)]=sh
     target=targets[str(h)];counts[('REAL',h,'AVAILABLE' if target['available'] else target['unavailable_reason'])]+=1
     counts[('SHIFT60',h,'AVAILABLE' if sh['available'] else sh['unavailable_reason'])]+=1
    s=structural(rows,i)
    structural_N['next_primary_available']+=int(s['next_primary_available']);structural_N['transition_window_available']+=int(s['transition_window_available']);structural_N['uncensored_transition_N']+=int(s.get('transition_within30')==1)
    x={'row_key':row['row_key'],'pair_id':row['pair_id'],'security_id':row['security_id'],'session_id':row['session_id'],'date':row['date'],'bar_end':row['bar_end'],'scheduled_t':row['scheduled_t'],'real':targets,'shift60':shift,'structural':s}
    writer.write(json.dumps(x,sort_keys=True,separators=(',',':'))+'\n');label_records_N+=1
  files.append({'path':str(t.relative_to(R)),'bytes':t.stat().st_size,'SHA256':digest(t)});all_dates.append(p['date'])
 dump('LABEL_FIXATION_RECEIPT.json',{'created_at_jst':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'status':'TARGETS_FIXED_FROM_ALREADY_FIXED_CAUSAL_FEATURES','feature_endpoint_N':features_N,'label_record_N':label_records_N,'unique_keys_N':len(keyset),'files':files,'target_denominators':[{'control':c,'horizon':h,'status_or_reason':s,'N':n} for (c,h,s),n in sorted(counts.items())],'structural_denominators':dict(structural_N),'input_date_N':len(set(all_dates)),'source_manifest_SHA256':digest(DATA/'DATASET_MANIFEST.json'),'contract_SHA256':pre['hashes']['PREDICTIVENESS_CONTRACT_V1.md'],'definition_changes':0,'protected_exposure':0,'price_labels_read_before_precommit':0})
 print(json.dumps({'label_records_N':label_records_N,'price_target_available_N':sum(n for (c,h,s),n in counts.items() if c=='REAL' and s=='AVAILABLE'),'date_N':len(set(all_dates)),'counts':[{'control':c,'h':h,'N':n} for (c,h,s),n in counts.items() if s=='AVAILABLE']}))
if __name__=='__main__':execute()
