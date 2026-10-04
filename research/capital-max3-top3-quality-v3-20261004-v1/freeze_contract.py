"""Freeze all design choices before new outcome measurements/models."""
from checkpoint import *
from core_features import NUMERIC,CATEGORICAL
control=json.loads((ROOT.parent/'capital_liquidity_off_private/LIQUIDITY_OFF_MAX3_RESULT.json').read_text())
assert control['funded_N']==167 and control['valid_primary_day_N']==38 and control['valid_rolling20_window_N']==19
model=json.loads((V2/'models/CORE_P_BLOCK_01.json').read_text())
assert NUMERIC==model['preprocessing']['numeric_fields'] and CATEGORICAL==model['preprocessing']['categorical_fields']
core={'numeric':NUMERIC,'categorical':CATEGORICAL}
save(OUT/'CORE_FEATURE_MANIFEST.json',core)
canonical=hashlib.sha256(json.dumps(core,sort_keys=True,separators=(',',':')).encode()).hexdigest()
save(OUT/'CONTROL_AND_OBJECTIVE_FREEZE.json',{'jst':now(),'control_result_head':CONTROL_HEAD,'control_profile':'CORE_P5_MAX3 + Liquidity Hard Reject OFF / capacity OFF','control_result_hash':sha(ROOT.parent/'capital_liquidity_off_private/LIQUIDITY_OFF_MAX3_RESULT.json'),'control_score_hash':sha(V2/'CORE_P5_SCORE_STREAM.jsonl.gz'),'control_metrics':{k:v for k,v in control.items() if k not in ('daily_series','rolling20_windows')},'CORE_canonical_manifest_hash':canonical,'CORE_existing_H5_canonical_manifest_hash':canonical,'CORE_manifest_identity':True,'control_replays':0,'H5_new_fits':0,'new_features':0,'Movement_added':0,'selection_baseline':{'funded_N':167,'PF1_N':54,'loss0_N':89,'tail1_N':58,'U3_N':73,'Medium_N':28,'U5_N':45,'U10_N':26,'below2_N':70,'below3_N':94},'North_Star':'JPY1000000 -> >=JPY2000000 / rolling20 supplied Development evaluation sessions','safety':SAFETY})
config={'version':'CAPITAL_QUALITY_V3_MAX3_ONE_SHOT_V1','jst':now(),'H5':'byte-identical existing CORE_P5 score; fits0',
 'new_heads':{'H3':'saved label_bigwinner3 ==1','HF1':'saved unconstrained realized_net_return >=0.01','HL0':'saved unconstrained realized_net_return <=0'},
 'realized_missing':'exclude only from HF1/HL0 training/evaluation labels; never zero-impute or runtime filter',
 'model':{'penalty':'l2','C':1.0,'solver':'lbfgs','max_iter':2000,'class_weight':None,'random_state':57},
 'preprocessing':'exact existing CORE train-only numeric missing0+indicator, mean/std population; train-only categorical vocab with explicit __UNKNOWN__',
 'temporal':{'sessions':58,'warmup':20,'OOF':38,'block_size':5,'last_block':3,'blocks':8,'H3_fits':8,'HF1_fits':8,'HL0_fits':8,'total_new_fits':24,'within_block_refits':0,'test_teacher_before_fit':'raw teacher IO indexed by identity only; label parsed only for completed training IDs; evaluation by separate post-fit module'},
 'lifts':{'L5':'existing pP/baseP','L3':'p3/base3','LF1':'p_floor1/base_floor1','LSAFE':'(1-p_loss0)/(1-base_loss0)'},
 'admission':'L3>=1 AND LF1>=1 AND LSAFE>=1','Q':'(L5*LF1*LSAFE)**(1/3)',
 'ordering':['Q DESC','L5 DESC','L3 DESC','Entry timestamp ASC','symbol stable ASC'],
 'rank':{'S':'Q>=2','A':'1.5<=Q<2','B':'1<=Q<1.5','C':'Q<1; gate PASS only =QUALIFIED_C'},
 'candidate_equity_caps':{'S':.45,'A':.35,'B':.25,'C':.15},'base_target_utilization':{'S':.68,'A':.56,'B':.44,'C':.30},'breadth_bonus':.055,'maximum_target_utilization':.92,
 'breadth_semantics':'existing held positions plus current selected candidates, as fixed CORE control; cap applies to BUY debit including factor once',
 'water_fill':'same batch initially funded candidates only; one-lot rounds in fixed order; no new identity; later top-up0',
 'profiles':['QUALITY_V3_MAX3','S_ONLY_MAX3','A_PLUS_MAX3','B_PLUS_MAX3'],'diagnostic_rank_sets':{'S_ONLY_MAX3':['S'],'A_PLUS_MAX3':['S','A'],'B_PLUS_MAX3':['S','A','B']},'diagnostic_adoption':False,
 'max_concurrent':3,'initial_cash':1000000,'lot':100,'liquidity_hard_reject':False,'liquidity_capacity_cap':False,'liquidity':'diagnostic only',
 'entry_cutoff_minute':920,'MTM':'MTM_LAST_ACTUAL_TRADE_SAME_SESSION_V1','EXIT':'Frozen EXIT v3 first; 15:20 full remaining SOR MARKET DAY; first admissible actual 15:20<=t<15:25; else exact15:30 auction; else fail closed',
 'execution_availability':'unchanged inherited completed-minute assumption (row minute+1); actual provider arrival UNKNOWN; no executable-depth guarantee',
 'BUY':1.0005,'SELL':.9995,'commission':0,'legacy_fee_added':0,
 'measurement_blocked':'no fabricated fill; blocked day null; after primary origin broken continue diagnostic days with JPY1m only; valid contiguous primary windows only',
 'slot_regret':'evaluation-only same-session same-entry-minute batch: selected FUNDED vs missed MAX_POSITION_CAP among admission/profile-eligible; report qualifying unique batches/candidates and pair N; incomplete realized outcomes excluded. Existing held positions can bind slots; no future replacement runtime.',
 'head_diagnostics':'OOF plus block ROC AUC, Brier, empirical base rate, deterministic top20% ceil(N*.2), ten equal-count bins stable p desc then identity; unknown labels excluded',
 'success_scoreboard':['PF1>Control','loss0<Control','tail1<Control','U5capture>Control','Mediumcapture>Control','U3capture>Control','below2<Control','below3<Control'],
 'selection_status':'IMPROVED iff PF1>,loss0<,U5capture>,Mediumcapture>; WORSE iff all four nonimproving; else MIXED',
 'economic_status':'IMPROVES iff geom and rolling20 median greater; WORSE iff both <=Control; else MIXED',
 'sweeps':0,'result_based_retune':0,'control_replays':0,'MAX4_MAX5_replays':0,'new_provider_requests':0,'exposure':EXPOSURE,'safety':SAFETY,'orders':0}
save(OUT/'DESIGN_PRECOMMIT.json',config)
checkpoint('Q1_CONTROL_AND_OBJECTIVE_FREEZE','QUALITY_V3_DESIGN_FROZEN',{'Main':1,'diagnostics':3,'new_fits_precommitted':24,'H5_new_fits':0,'CORE_manifest_identity':True,'CORE_manifest_canonical_hash':canonical},next_direction='Confirm saved teacher census without feature or design changes.')
