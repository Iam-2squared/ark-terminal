"""Read-only, outcome-free packet adapter. Never imports a V5 runner or inference code."""
import json,gzip,hashlib,struct,pathlib,datetime,collections
ROOT=pathlib.Path('/workspace/scratch/f3d0aa747c89');BASE=ROOT/'bridge_work';OUT=BASE/'evidence';PRIVATE=BASE/'private'
HEADS=('pP','MOVE_U2','MOVE_U3','MRET')
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def digest(ids):return hashlib.sha256(json.dumps(sorted(ids),separators=(',',':')).encode()).hexdigest()
def read(path):return json.loads(pathlib.Path(path).read_text())
def rows(path):
 with gzip.open(path,'rt') as f:return [json.loads(l) for l in f]
def now():return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
def save(name,obj,private=False):
 p=(PRIVATE if private else OUT)/name;p.parent.mkdir(parents=True,exist_ok=True)
 if name.endswith('.jsonl.gz'):
  b=gzip.compress(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n' for r in obj).encode(),mtime=0)
 else:b=(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
 if p.exists():assert p.read_bytes()==b,'IMMUTABLE_OUTPUT_CONFLICT:'+str(p)
 else:p.write_bytes(b)
 return sha(p)
def long_wide(rr):
 d={}
 for r in rr:
  k,h=r['entry_id'],r['head'];assert h in HEADS
  assert h not in d.setdefault(k,{}),'DUPLICATE_HEAD'
  d[k][h]=r
 assert all(set(v)==set(HEADS) for v in d.values())
 return d
def fraction(t,s):
 if s is None:return {'numerator':None,'denominator':None,'LOW':None,'HIGH':None}
 n=1+sum(v<s for v in t);d=len(t)+1
 return {'numerator':n,'denominator':d,'LOW':2*n<d,'HIGH':2*n>=d}
def support(snapshot,packet,channel):
 """Structural support only. No outcome, threshold, intent or V5 state transition."""
 if channel=='FULL_MAX3':return {'support':False,'unknown':False,'reason':'ENTRY_COMPARISON_ONLY_EXIT_FROZEN'}
 if any(packet['heads'][h]['available'] is not True for h in HEADS):return {'support':False,'unknown':True,'reason':'MISSING_ASOF_SCORE'}
 if snapshot is None:return {'support':False,'unknown':True,'reason':'MISSING_SAVED_SNAPSHOT'}
 n=snapshot.get('existing_open_N');quantity=snapshot.get('planned_quantity');reason=packet['native']['reason']
 if n is None:return {'support':False,'unknown':True,'reason':'MISSING_CURRENT_OCCUPANCY'}
 if channel=='PRE_BUY_DEFENSE':return {'support':quantity is not None and quantity>=100,'unknown':quantity is None,'reason':'NATIVE_PLANNED_PRE_BUY_ONLY'}
 if channel=='VACANT_SLOT_RESERVE':return {'support':n<3 and reason=='SLOT_RESERVE_REJECT','unknown':False,'reason':'VACANCY_ONLY_ALLOCATION_NOT_PROVEN'}
 if channel=='PRE_BUY_SAME_BATCH':return {'support':snapshot.get('same_batch_candidate_N',0)>1,'unknown':False,'reason':'SAME_TIMESTAMP_COMPARISON_ONLY'}
 return {'support':False,'unknown':False,'reason':'ORIGINAL_CONSTRAINT_NOT_AUTHORIZED'}
def main():
 current=rows(ROOT/'r1_work/score_certification/CURRENT_FOUR_HEAD_INTELLIGENCE.jsonl.gz');assert len(current)==1039
 refs=read(ROOT/'r1_work/score_certification/TRAINING_REFERENCE_POPULATIONS.json');ref={(r['block'],r['head']):r for r in refs};assert len(ref)==32
 decisions=rows(ROOT/'r1_work/runs/OFF_PRIMARY/DECISIONS.jsonl.gz');dd={r['entry_id']:r for r in decisions};assert len(dd)==1039
 proposals=rows(ROOT/'r1_work/runs/OFF_PRIMARY/NATIVE_PROPOSALS.jsonl.gz')
 runtime=rows(ROOT/'r1_work/inputs/v8r1/inputs/movement/RUNTIME_CAUSAL.jsonl.gz');rr={r['entry_id']:r for r in runtime};assert len(rr)==len(runtime)
 common=rows(ROOT/'r1_work/inputs/quality/private/COMMON_SAVED_SCORES.jsonl.gz')
 # Original evaluation mask, not the full1039 prediction stream. No labels copied.
 mret=[{'entry_id':r['entry_id']} for r in rows(BASE/'sources/mret/private/MRET_EVALUATION_ROWS.jsonl.gz')]
 wide=long_wide(rows(ROOT/'r1_work/metrics/supplement/V5_FUNDED150_FOUR_SCORE_NATIVE_SLOT.jsonl.gz'));assert len(wide)==150
 keys=[r['entry_id'] for r in current];assert len(set(keys))==1039 and set(keys)==set(dd)
 models={};registry=[]
 for (block,head),r in sorted(ref.items()):
  if head=='pP':p=ROOT/f'r1_work/inputs/v8r1/inputs/movement/models/MOVE_P_BLOCK_{block:02}.json'
  elif head=='MRET':p=ROOT/f'r1_work/inputs/mret/private/models/MRET_BLOCK_{block:02}.json'
  else:p=ROOT/f'r1_work/inputs/quality/private/models/{head}_BLOCK_{block:02}.json'
  model=read(p);assert sha(p)==r['model_sha256'],str(p)
  assert r['reference_N']==len(r['scores'])==len(r['train_identity_order'])==len(r['ordered_reference'])
  assert [x['entry_id'] for x in r['ordered_reference']]==r['train_identity_order']
  assert all(x['session']<=model['train_through'] for x in r['ordered_reference'])
  models[(block,head)]=model
  registry.append({'block':block,'head':head,'model_sha256':sha(p),'reference_N':r['reference_N'],'training_reference_hash':r['train_identity_sha256'],'train_through':model['train_through'],'test_dates':model['test_dates'],'reference_use':'RESUBSTITUTION_PERCENTILE_NOT_OOF_PERFORMANCE'})
 sources={p:sha(ROOT/p) for p in ['r1_work/score_certification/CURRENT_FOUR_HEAD_INTELLIGENCE.jsonl.gz','r1_work/score_certification/TRAINING_REFERENCE_POPULATIONS.json','r1_work/runs/OFF_PRIMARY/DECISIONS.jsonl.gz','r1_work/runs/OFF_PRIMARY/NATIVE_PROPOSALS.jsonl.gz','r1_work/inputs/v8r1/inputs/movement/RUNTIME_CAUSAL.jsonl.gz','r1_work/metrics/supplement/V5_FUNDED150_FOUR_SCORE_NATIVE_SLOT.jsonl.gz']}
 packet=[];copy_N=0
 for r in current:
  k=r['entry_id'];a=rr[k];d=dd[k];block=r['block']
  assert r['session']==a['session']==d['session'] and r['entry_minute']==a['entry_minute']==d['minute']
  # Final source minute is strictly before Entry; models frozen before test session.
  source_max=a['movement_provenance']['current_max_source_minute'];assert source_max<a['entry_minute']
  item={'entry_id':k,'session':r['session'],'symbol':a['symbol'],'frozen_entry_time':a['entry_timestamp'],'entry_minute':r['entry_minute'],'native_block':block,'source_hashes':sources,'native':{n:d.get(n) for n in ['ML','rank','reason','slot_admission_index','funded_slot']},'heads':{}}
  for h in HEADS:
   v=r[h];t=ref[(block,h)];f=fraction(t['scores'],v['score']);assert f['numerator']==v['rank_numerator'] and f['denominator']==v['rank_denominator'] and f['LOW']==v['LOW'] and f['HIGH']==v['HIGH']
   model=models[(block,h)];assert model['train_through']<r['session'] and r['session'] in model['test_dates']
   item['heads'][h]={'raw_score':v['score'],'model_hash':v['model_sha256'],'training_reference_hash':v['reference_sha256'],'numerator':f['numerator'],'denominator':f['denominator'],'LOW':f['LOW'],'HIGH':f['HIGH'],'score_asof':a['entry_timestamp'],'feature_max_source_minute':source_max,'prediction_origin':{'kind':'SAVED_CURRENT_OOF_FIXED_HEAD','train_through':model['train_through'],'block':block},'available':True,'unavailable_reason':None}
   assert struct.pack('>d',item['heads'][h]['raw_score'])==struct.pack('>d',v['score']);copy_N+=1
   if k in wide:
    w=wide[k][h];assert struct.pack('>d',w['score'])==struct.pack('>d',v['score']) and w['native_funded_slot']==d['funded_slot']
  packet.append(item)
 ph=save('FROZEN_EXPERT_PACKET.jsonl.gz',packet,True)
 cohorts={'C0':[r['entry_id'] for r in common],'C1':[r['entry_id'] for r in mret],'C2':sorted(wide),'C3':[k for k,d in dd.items() if d['admission'] is True],'C4':{reason:[k for k,d in dd.items() if d['admission'] is True and d['reason']==reason] for reason in sorted({d['reason'] for d in dd.values() if d['admission'] is True})},'C5':[{'session':r['session'],'minute':r['minute'],'entry_ids':[c['entry_id'] for c in r['candidates']]} for r in proposals], 'C6':[{'block':r['block'],'head':r['head'],'N':r['reference_N'],'identity_order_hash':r['train_identity_sha256']} for r in refs]}
 assert len(cohorts['C0'])==1028 and len(cohorts['C1'])==1016 and len(cohorts['C2'])==150
 assert set(cohorts['C1'])<=set(cohorts['C0']);assert len(cohorts['C3'])==494
 save('COHORT_MASKS.json',cohorts,True)
 # Outcome-free sanitized snapshots exclude any saved exit, future prices or labels.
 snapshots=[]
 for b in proposals:
  assigned={a['entry_id']:a for a in b['assigned']};prior_success=0
  for c in b['candidates']:
   k=c['entry_id'];a=assigned.get(k);q=a['quantity'] if a else None
   planned_slot=b['existing_open_N']+prior_success+1 if a and q>=100 else None
   sn={'entry_id':k,'session':b['session'],'minute':b['minute'],'existing_open_N':b['existing_open_N'],'position_ids':sorted(b['snapshot']['positions']),'cash':b['snapshot']['cash'],'equity':b['snapshot']['equity'],'exposure':b['snapshot']['exposure'],'native_picked_ids':b['picked_ids'],'same_batch_candidate_N':len(b['candidates']),'planned_quantity':q,'planned_slot':planned_slot,'lot_debit':a.get('lot_debit') if a else None,'native_sequence_index':next((i for i,x in enumerate(b['picked_ids'],1) if x==k),None)}
   snapshots.append(sn)
   if a and q>=100:prior_success+=1
 sh=save('SAVED_OUTCOME_FREE_SNAPSHOTS.jsonl.gz',snapshots,True)
 save('EXPERT_REGISTRY.json',{'frozen_head_models':registry,'head_roles':{'pP':'Winner priority U5; U10 secondary','MOVE_U2':'Potential>=2, Weak counterpart','MOVE_U3':'Potential>=3 cumulative','MRET':'same native Potential-bucket relative monetization'},'new_fit':0,'new_inference':0,'old_statuses_unchanged':True})
 save('REUSE_AND_NOVEL_WORK.json',{'reuse':['existing original head score streams/masks/model hashes','training references32','original independent numerical certificates','OFF saved ledgers','funded150 long600','R1 NO_EFFECT and trigger0'],'novel':['read-only outcome-free packet','conditional metric and wrong-exclusion diagnostics','all signed MRET controls','rank conflict and channel census','two unexecuted design cards'],'PnL_join_before_packet':0,'new_market_replays':0})
 save('ROLE_CONTRACT.json',{'roles':'separate raw-score ranks; no scalar or runtime blend','permanent_freeze':['Selector','Entry','EXIT'],'Capital':'NOT_EVALUATED','diagnostic_labels_not_intents':True,'legal_channels':['pre-BUY native ADMIT diagnostics','vacant Reserve opportunities'],'illegal':['forced exit','partial sale','replacement','missed old Entry re-buy'],'asof_source_check':'feature max source minute < Frozen Entry; all train_through < test session; original certificates reused','support_checker':'pure snapshot/packet -> support/unknown/reason; no labels or action emission'})
 save('F2_PACKET_FREEZE_RECEIPT.json',{'exact_jst':now(),'packet_sha256':ph,'snapshot_sha256':sh,'packet_N':1039,'raw_binary64_copies':copy_N,'funded_long_rows':600,'funded_unique_transactions':150,'native_funded_slots':dict(collections.Counter(dd[k]['funded_slot'] for k in wide)),'C0_N':1028,'C1_N':1016,'C1_missing_from_C0_N':len(set(cohorts['C0'])-set(cohorts['C1'])),'C3_N':494,'cohort_masks_sha256':sha(PRIVATE/'COHORT_MASKS.json'),'outcome_join_N':0,'all_asof_checks':'PASS','L1':'PASS','L2':'PENDING_ORIGINAL_MASK_REPRODUCTION','L3':'NOT_EVALUATED','currentInference':0,'next':'actual GET packet hash receipt then outcome-only join'})
 print(json.dumps(read(OUT/'F2_PACKET_FREEZE_RECEIPT.json')))
if __name__=='__main__':main()
