"""Separate saved-case reconstruction; imports no Primary gate, allocator or evaluator.

This process never runs a market path or calls an RNG. It reconstructs identities,
current batch outputs, singleton funding, and past screens from original sources;
bootstrap arithmetic uses the already committed resample counts.
"""
from pathlib import Path
from decimal import Decimal, ROUND_FLOOR
from fractions import Fraction
from collections import Counter, defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
import gzip, hashlib, json, math, struct

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT.parent/'work/bridge_private'
OUT=ROOT/'docs/evidence/capital-v5-reserve-past-qualified-20261005-v1'
PRIVATE=ROOT.parent/'work/r_work/private'
D=Decimal
ROLES={
 'packet':'bridge_work/private/FROZEN_EXPERT_PACKET.jsonl.gz',
 'reference32':'r1_work/score_certification/TRAINING_REFERENCE_POPULATIONS.json',
 'canonical_scores':'r1_work/score_certification/CURRENT_FOUR_HEAD_INTELLIGENCE.jsonl.gz',
 'proposals':'r1_work/runs/OFF_PRIMARY/NATIVE_PROPOSALS.jsonl.gz',
 'decisions':'r1_work/runs/OFF_PRIMARY/DECISIONS.jsonl.gz',
 'trades':'r1_work/runs/OFF_PRIMARY/TRADES.jsonl.gz',
 'arrival':'r1_work/inputs/v5/repo/docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1/ARRIVAL_TABLE.json',
 'split':'r1_work/inputs/v5_source/repo/docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json',
 'teachers':'r1_work/metrics/evaluation_only/TEACHERS_EVALUATION.jsonl.gz',
 'outcomes':'r1_work/metrics/evaluation_only/OUTCOMES_EXACT_EVALUATION.json'}
HEADS=('pP','MOVE_U2','MOVE_U3')
RESERVE=('SLOT2_RESERVE_FOR_FUTURE_QUALITY','SLOT3_RESERVE_FOR_FUTURE_QUALITY')
CHECKS=Counter()

def load_file(p):
    if p.suffix=='.gz':
        with gzip.open(p,'rt',encoding='utf-8') as f:return [json.loads(s) for s in f]
    return json.loads(p.read_text(encoding='utf-8'))
def original(name):return load_file(BASE/ROLES[name])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def raw_digest(o):return hashlib.sha256(json.dumps(o,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def require(ok,kind,detail=''):
    CHECKS[kind]+=1
    if not ok:raise AssertionError(kind+':'+str(detail))
def eq(a,b,kind,detail=''):require(a==b,kind,detail)
def frac(x):return Fraction(D(str(x)))
def textfrac(x):return str(x.numerator)+'/'+str(x.denominator)
def scalar(x):
    if isinstance(x,D):return str(x)
    if isinstance(x,list):return [scalar(y) for y in x]
    if isinstance(x,dict):return {k:scalar(v) for k,v in x.items()}
    return x
def save(name,obj,private=False):
    p=(PRIVATE if private else OUT)/name;p.parent.mkdir(parents=True,exist_ok=True)
    require(not p.exists(),'append_only_new_output',name)
    p.write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    return p

def category(score):
    if score is None or not math.isfinite(score) or score<1:return None
    return 'S' if score>=2 else 'A' if score>=1.5 else 'B'
def priority(r):return (-r['ML'],-r['m5'],-r['m3'],-r['m2'],r['entry_timestamp'],r['symbol'])
def own_allocate(rows,state):
    equity=D(state['equity']);cash=D(state['cash']);exposure=D(state['exposure'])
    caps={'S':D('.45'),'A':D('.35'),'B':D('.25')};base={'S':D('.68'),'A':D('.56'),'B':D('.44')}
    bands=[p['band'] for p in state['positions'].values()]+[category(r['capital_score']) for r in rows]
    best=sorted(bands,key=('S','A','B').index)[0]
    target=min(D('.92'),base[best]+D('.055')*(len(bands)-1))
    budget=min(cash,max(D(0),equity*target-exposure))
    weight_total=sum(D(str(r['capital_score'])) for r in rows)
    left_cash=cash;left_budget=budget;answers=[]
    for row in rows:
        band=category(row['capital_score']);lot=D(row['raw_reference'])*D('1.0005')*100
        desired=budget*D(str(row['capital_score']))/weight_total;cap=equity*caps[band]
        lots=max(0,int((min(desired,cap,left_cash)/lot).to_integral_value(rounding=ROUND_FLOOR)))
        debit=lots*lot;left_cash-=debit;left_budget-=debit
        answers.append({'entry_id':row['entry_id'],'quantity':lots*100,'first_pass_quantity':lots*100,
            'water_fill_lots':0,'debit':debit,'lot_debit':lot,'equity_cap':cap,'liquidity_cap':None,
            'desired':desired,'band':band,'target_utilization':target,'batch_equity':equity,'batch_budget':budget})
    rounds=0
    while True:
        changed=False
        for a in answers:
            if a['first_pass_quantity']==0:continue
            lot=a['lot_debit']
            if left_cash>=lot and left_budget>=lot and a['debit']+lot<=a['equity_cap']:
                left_cash-=lot;left_budget-=lot;a['debit']+=lot;a['quantity']+=100;a['water_fill_lots']+=1;changed=True
        if not changed:break
        rounds+=1
    for a in answers:a.update(water_fill_rounds=rounds,budget_unspent=left_budget)
    return scalar(answers)
def own_gate(row,occupancy,minute,table):
    counts=table['minute_counts'][str(minute)];n=table['training_session_N']
    prob=counts[0]/n;expected=counts[2]/n
    extra={'pre_decision_occupancy':occupancy,'training_B_median':table['B_median'],
        'training_B_p75':table['B_p75'],'remaining_Aplus_probability':prob,
        'remaining_Aplus_ge2_probability':counts[1]/n,'expected_remaining_Aplus':expected,
        'arrival_bucket':table['minute_bucket'][str(minute)],'training_block':row['block']}
    if occupancy==3:return False,'MAX_POSITION_CAP',extra
    if occupancy==0:return True,'SLOT1_NO_RESERVE',extra
    if row['rank'] in ('S','A'):return True,'SA_ALWAYS_ADMIT',extra
    require(row['rank']=='B','native_gate_B_only')
    if occupancy==1:
        allowed=minute>=840 or (row['ML']>=table['B_median'] and prob<.5)
        reason='SLOT2_B_LATE_RELEASE' if minute>=840 else 'SLOT2_B_QUALITY_AND_ARRIVAL_PASS' if allowed else RESERVE[0]
    else:
        allowed=row['ML']>=table['B_p75'] and (minute>=870 or (prob<.35 and expected<.75))
        reason='SLOT3_B_LATE_RELEASE' if allowed and minute>=870 else 'SLOT3_B_QUALITY_AND_ARRIVAL_PASS' if allowed else RESERVE[1]
    return allowed,reason,extra
def own_native(p,table):
    state=p['snapshot'];picked=[];decisions=[]
    for row in sorted(p['candidates'],key=priority):
        eq((row['session'],row['entry_minute']),(p['session'],p['minute']),'native_same_current_batch')
        d={'entry_id':row['entry_id'],'reason':None};decisions.append(d)
        if p['minute']>=920:d['reason']='CAPITAL_EOD_ENTRY_CUTOFF';continue
        if not row['admission']:d['reason']='UPWARD_BELOW_BASELINE';continue
        if category(row['capital_score']) is None:d['reason']='SCORE_INPUT_UNKNOWN';continue
        if any(pos['symbol']==row['symbol'] for pos in state['positions'].values()):d['reason']='SYMBOL_ALREADY_OPEN';continue
        allowed,reason,audit=own_gate(row,len(state['positions'])+len(picked),p['minute'],table)
        d.update(audit,slot_gate_reason=reason,slot_gate_action='ADMIT' if allowed else 'REJECT')
        if not allowed:d['reason']='SLOT_RESERVE_REJECT' if reason in RESERVE else reason;continue
        d['slot_admission_index']=len(state['positions'])+len(picked)+1;picked.append(row)
    assigned=own_allocate(picked,state) if picked else []
    return {'picked_ids':[r['entry_id'] for r in picked],'gate_decisions':decisions,'assigned':assigned}
def own_scores(record):
    return {h:{k:record['heads'][h][k] for k in ('raw_score','numerator','denominator','available',
        'score_asof','feature_max_source_minute','prediction_origin','model_hash','training_reference_hash')} for h in HEADS}
def own_score_pass(scores):
    for s in scores.values():
        if not s['available'] or not math.isfinite(s['raw_score']):return False,'SCORE_UNKNOWN_ABSTAIN'
        if not isinstance(s['numerator'],int) or not isinstance(s['denominator'],int) or not 1<=s['numerator']<=s['denominator']:
            return False,'REFERENCE_UNKNOWN_ABSTAIN'
    p,q2,q3=(scores[h] for h in HEADS)
    if Fraction(p['numerator'],p['denominator'])<Fraction(3,4):return False,'WINNER_RANK_BELOW_3_4'
    if all(Fraction(s['numerator'],s['denominator'])<Fraction(1,2) for s in (q2,q3)):return False,'BOTH_QUALITY_LOW'
    return True,'SCORE_PASS'
def singleton_reason(a,state):
    if a['quantity']>=100:return 'FUNDABLE'
    if D(state['cash'])<D(a['lot_debit']):return 'CASH_BELOW_1LOT'
    if D(a['batch_budget'])<D(a['lot_debit']):return 'CASH_AVAILABLE_TARGET_BUDGET_BELOW_1LOT'
    if D(a['equity_cap'])<D(a['lot_debit']):return 'CAP_BELOW_1LOT'
    return 'ALLOCATION_QUANTITY_ZERO'

def mature_label(row,teacher,outcome,current_start):
    t=teacher;o=outcome
    require(t is not None and o is not None,'past_label_identity_present',row['entry_id'])
    eq((t['session'],row['block']<current_start['block']),(row['session'],True),'prior_OOF_label_identity')
    require(t['capture_complete'] is True and t['strictly_after_entry_before_1520'] is True,'potential_label_horizon')
    require(t['execution_status']=='COMPLETE' and o['frozen_execution_status']=='COMPLETE','saved_settlement_complete')
    require(t['source_minute'] is not None and t['source_lineage'] and 0<=t['release_minute']<=931,'saved_label_source_bound')
    bound=row['session']+'T15:31:00+09:00';cutoff=min(current_start['test'])+'T09:00:00+09:00'
    require(datetime.fromisoformat(bound)<datetime.fromisoformat(cutoff),'label_matured_before_block')
    potential=frac(o['potential_pct']);net=frac(o['frozen_realized_net_return_cell'])
    eq(potential,frac(t['potential_return'])*100,'original_potential_copy')
    eq(net,frac(t['realized_net_return']),'original_net_return_copy')
    return {'entry_id':row['entry_id'],'session':row['session'],'block':row['block'],
        'potential':potential,'net':net,'label_maturity_bound':bound,
        'targets':{'U5':potential>=5,'U10':potential>=10,'U3':potential>=3,'Weak':potential<2,'realized_nonpositive':net<=0}}
def percent(values,p):
    a=sorted(values);position=(len(a)-1)*p;low=math.floor(position);high=math.ceil(position)
    return a[low]+(a[high]-a[low])*(position-low)
def own_screen(block,frame,S,F,counts):
    n=len(S);m=len(F);sc={k:sum(r['targets'][k] for r in S) for k in ('U5','U10','U3','Weak','realized_nonpositive')}
    fc={k:sum(r['targets'][k] for r in F) for k in sc}
    need={'S_N':max(0,10-n),'S_sessions':max(0,10-len({r['session'] for r in S})),
        'S_blocks':max(0,2-len({r['block'] for r in S})),'F_N':max(0,20-m),
        'F_sessions':max(0,8-len({r['session'] for r in F})),'S_U5':max(0,2-sc['U5']),'S_U10':max(0,1-sc['U10'])}
    H={'H0':block!=1,'H1':not any(need.values()),'H2':False,'H3':False,'H4':False,'H5':False,'H6':False}
    avg=None;loo={};ci=None
    if n:
        total=sum((r['net'] for r in S),Fraction(0));avg=total/n
        H['H2']=avg>0;loo={r['session']:textfrac((total-r['net'])/(n-1)) for r in S} if n>1 else {}
        H['H4']=bool(loo) and min(Fraction(s) for s in loo.values())>0
        returns={r['session']:r['net'] for r in S};eq(len(returns),n,'one_S_per_session')
        x=[float(returns.get(s,Fraction(0))) for s in frame];values=[]
        eq(len(counts),1999,'bootstrap_valid_count')
        for i,sample in enumerate(counts):
            eq(sample['resample'],i,'bootstrap_saved_order');eq(sample['frame'],frame,'bootstrap_prior_frame')
            eq(len(sample['counts']),len(frame),'bootstrap_count_dimension');eq(sum(sample['counts']),len(frame),'bootstrap_frame_draw_size')
            require(all(isinstance(c,int) and c>=0 for c in sample['counts']),'bootstrap_nonnegative_counts')
            value=math.fsum(c*v for c,v in zip(sample['counts'],x))/len(frame)
            require(math.isfinite(value) and abs(value-sample['mean'])<=1e-12,'bootstrap_saved_mean_reconstruction')
            values.append(value)
        ci=[percent(values,.025),percent(values,.975)];H['H3']=ci[0]>0
        if m:
            H['H5']=all(Fraction(sc[k],n)>=Fraction(fc[k],m) for k in ('U5','U10','U3'))
            H['H6']=all(Fraction(sc[k],n)<=Fraction(fc[k],m) for k in ('Weak','realized_nonpositive'))
    return {'block':block,'Hi':H,'PAST_QUALIFIED':all(H.values()),'S_counts':sc,'F_counts':fc,
        'support_shortfalls':need,'mean_exact':textfrac(avg) if avg is not None else None,'loo_exact':loo,'CI95':ci,
        'S_ids':[r['entry_id'] for r in S],'F_ids':[r['entry_id'] for r in F],'frame_sessions':frame}

def main():
    manifest=load_file(OUT/'PAST_PROPOSAL_MANIFEST.json');tables=load_file(OUT/'PAST_QUALIFICATION_BY_BLOCK.json')['tables']
    eq(sha(PRIVATE/'PAST_PROPOSALS_OUTCOME_BLIND.jsonl.gz'),manifest['S_artifact_sha256'],'frozen_S_bytes')
    packet=original('packet');byid={r['entry_id']:r for r in packet};canonical={r['entry_id']:r for r in original('canonical_scores')}
    references={(r['block'],r['head']):r for r in original('reference32')};split=original('split')
    for record in packet:
        for h in HEADS:
            s=record['heads'][h];old=canonical[record['entry_id']][h];ref=references[record['native_block'],h]
            eq(struct.pack('>d',s['raw_score']),struct.pack('>d',old['score']),'binary64_score_copy')
            eq(s['numerator'],1+sum(t<s['raw_score'] for t in ref['scores']),'strict_less_original_reference_rank')
            eq(s['denominator'],len(ref['scores'])+1,'head_specific_denominator')
            eq(s['model_hash'],ref['model_sha256'],'original_head_model_hash')
            require(all(r['session']<record['session'] for r in ref['ordered_reference']),'completed_training_reference')
    probes=load_file(PRIVATE/'SHADOW_NATIVE_SNAPSHOT_PROBES.jsonl.gz');probes_byindex={p['snapshot_index']:p for p in probes}
    proposals=original('proposals');arrival=original('arrival');ownS=[];ended=set();records=[];fund_reasons=Counter()
    final_decisions={r['entry_id']:r for r in original('decisions')}
    for index,p in enumerate(proposals):
        n=own_native(p,arrival[str(p['candidates'][0]['block'])]);eq(n['picked_ids'],p['picked_ids'],'native_picked_identity',index)
        eq(n['assigned'],p['assigned'],'native_allocation_output_exact',index)
        saved_gate={d['entry_id']:d for d in p['gate_decisions']}
        eq(len(n['gate_decisions']),len(p['candidates']),'native_all_input_rows_accounted')
        eq({d['entry_id'] for d in n['gate_decisions'] if 'slot_gate_reason' in d},set(saved_gate),'native_gate_identity_population')
        for d in n['gate_decisions']:
            if d['entry_id'] in saved_gate:
                for k,v in d.items():eq(v,saved_gate[d['entry_id']].get(k),'native_gate_field_exact',str(index)+':'+k)
            else:
                require(d['reason'] in ('UPWARD_BELOW_BASELINE','CAPITAL_EOD_ENTRY_CUTOFF','SCORE_INPUT_UNKNOWN','SYMBOL_ALREADY_OPEN'),'native_filter_only_row')
                eq(d['reason'],final_decisions[d['entry_id']]['reason'],'native_filter_final_saved_reason')
                eq(final_decisions[d['entry_id']]['quantity'],0,'native_filter_saved_zero_quantity')
        ds={d['entry_id']:d for d in n['gate_decisions']}
        pool=[r for r in sorted(p['candidates'],key=priority) if r['rank']=='B' and r['admission'] and r['ML']>=1 and ds[r['entry_id']].get('slot_gate_reason') in RESERVE]
        if not pool or n['picked_ids']:continue
        require(len(p['snapshot']['positions']) in (1,2) and p['minute']<920,'structural_actual_state')
        require(all(byid[r['entry_id']]['heads']['pP']['available'] for r in pool),'pool_all_pP_known')
        row=sorted(pool,key=lambda r:-byid[r['entry_id']]['heads']['pP']['raw_score'])[0];key=row['entry_id']
        scores=own_scores(byid[key]);passed,reason=own_score_pass(scores)
        for s in scores.values():
            require(s['score_asof']==row['entry_timestamp'] and s['feature_max_source_minute']<p['minute'] and s['prediction_origin']['train_through']<p['session'],'selected_score_asof')
        a=own_allocate([row],p['snapshot'])[0];why=singleton_reason(a,p['snapshot']);a['fundability_reason']=why
        require(D(a['debit'])<=min(D(p['snapshot']['cash']),D(a['batch_budget']),D(a['equity_cap'])),'singleton_cash_budget_cap')
        probe=probes_byindex[index];eq(key,probe['candidate'],'raw_pP_first_identity');eq([r['entry_id'] for r in pool],probe['pool_ids'],'native_stable_pool_order')
        eq(a,probe['allocation'],'singleton_allocation_exact',index);eq(passed,probe['score_pass'],'score_gate_exact')
        eq(reason if not passed else why,probe['reason'],'snapshot_final_reason');eq(scores,probe['scores'],'selected_score_bits_and_provenance')
        fund_reasons[why]+=1
        if passed and a['quantity']>=100 and p['session'] not in ended:
            ownS.append({'entry_id':key,'session':p['session'],'block':row['block'],'minute':p['minute'],
                'snapshot_index':index,'snapshot_hash':raw_digest(p),'native_reason':ds[key]['slot_gate_reason'],
                'quantity':a['quantity'],'debit':a['debit'],'allocation':a,'scores':scores});ended.add(p['session'])
        records.append({'snapshot_index':index,'candidate':key,'quantity':a['quantity'],'debit':a['debit'],'score_pass':passed,'reason':why})
    eq(ownS,load_file(PRIVATE/'PAST_PROPOSALS_OUTCOME_BLIND.jsonl.gz'),'first_one_fundable_S_full_exact')
    eq(raw_digest(ownS),manifest['S_canonical_identity_hash'],'outcome_blind_S_identity_hash')
    # Outcomes are opened only after independent outcome-blind S is fixed and compared.
    teachers={r['entry_id']:r for r in original('teachers')};outcomes=original('outcomes');trades=original('trades')
    block_of={s:b['block'] for b in split['blocks'] for s in b['test']}
    allcounts=load_file(PRIVATE/'PAST_BOOTSTRAP_SESSION_COUNTS.jsonl.gz');counts=defaultdict(list)
    for r in allcounts:counts[r['block']].append(r)
    own_tables=[]
    for b,primary in zip(split['blocks'],tables):
        number=b['block'];frame=[s for s in split['OOF38'] if block_of[s]<number]
        ss=[r for r in ownS if r['block']<number];ff=[r|{'block':block_of[r['session']]} for r in trades if block_of[r['session']]<number]
        S=[mature_label(r,teachers[r['entry_id']],outcomes[r['entry_id']],b) for r in ss]
        F=[mature_label(r,teachers[r['entry_id']],outcomes[r['entry_id']],b) for r in ff]
        t=own_screen(number,frame,S,F,counts[number]);own_tables.append(t)
        for k in ('Hi','PAST_QUALIFIED','S_ids','F_ids','frame_sessions','support_shortfalls'):eq(t[k],primary[k],'qualification_'+k,number)
        eq(t['S_counts'],primary['S']['target_counts'],'qualification_S_target_counts')
        eq(t['F_counts'],primary['F']['target_counts'],'qualification_F_target_counts')
        eq(t['mean_exact'],primary['metrics']['mean_S_net_return_exact'],'qualification_mean_rational')
        eq(t['loo_exact'],primary['metrics']['leave_one_session_means_exact'],'qualification_leave_one_session_rational')
        if t['CI95'] is not None:
            require(all(abs(a-b)<=1e-12 for a,b in zip(t['CI95'],primary['metrics']['bootstrap_CI95'])),'qualification_CI_linear_percentiles')
        else:eq(primary['metrics']['bootstrap_CI95'],None,'cold_no_bootstrap')
        for cohort in ('S','F'):eq(primary[cohort]['unknown_N'],0,'no_required_unknown_past_labels')
    p=save('INDEPENDENT_PREMAIN_RECONSTRUCTION.json',{'probes':records,'tables':own_tables},private=True)
    audit={'schema':'V5_R_INDEPENDENT_AUDIT_V1','exact_jst':datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),
        'status':'PASS','pre_main_mismatch_N':0,'mismatch_N':0,'checks':dict(CHECKS),'check_N':sum(CHECKS.values()),
        'independent_code_sha256':sha(Path(__file__)),'original_source_hashes':{k:sha(BASE/v) for k,v in ROLES.items()},
        'reconstruction_artifact':'private/INDEPENDENT_PREMAIN_RECONSTRUCTION.json','reconstruction_sha256':sha(p),
        'native_saved_batch_N':len(proposals),'selected_snapshot_N':len(records),'S_N':len(ownS),'past_table_N':len(own_tables),
        'qualified_block_N':sum(t['PAST_QUALIFIED'] for t in own_tables),'saved_bootstrap_counts_N':len(allcounts),
        'new_bootstrap_draws':0,'new_model_inference':0,'market_replay_N':0,
        'imports_primary_gate_allocation_evaluator':False,'independent_R_reconstruction':{'status':'NOT_EXECUTED','N':0,'reason':'All8 PAST_QUALIFIED false; Primary R Replay not authorized by fixed gate'},
        'first_divergence_prefix_scan':{'status':'NOT_EXECUTED','N':0,'reason':'PAST_SUPPORT_NOT_ESTABLISHED takes priority'},
        'limits':['Separate implementation by same researcher; shared original score/reference/source assets, not blind external audit.',
            'Decimal28 and original immutable sources are shared numerical authorities.',
            'Label maturity uses the inherited assumed closed-bar completed-session contract and saved source bounds; actual historical provider delivery remains UNKNOWN.',
            'No executed R trade, MTM, daily or19-window reconstruction exists because R was not executed.']}
    save('INDEPENDENT_AUDIT.json',audit)
    save('NATIVE_SINGLETON_FUNDABILITY.json',{'schema':'V5_R_NATIVE_SINGLETON_FUNDABILITY_V1','status':'PASS',
        'native_source_formula_correspondence':'CAP/BASE/target/budget/lot100/BUY1.0005/first-pass/water-fill checked against source and separate implementation',
        'primary_native_singleton_calls':len(records),'per_selected_actual_snapshot_call_max':1,'snapshot_state_mutation_N':0,
        'native_wrapper_OFF_saved_batch_N':len(proposals),'new_OFF_market_replays':0,'independent_mismatch_N':0,
        'diagnostic_selected_snapshot_N':len(records),'snapshot_fundable_N':sum(r['quantity']>=100 for r in records),
        'fundability_reasons':dict(fund_reasons),'outcome_blind_first_per_session_proposal_N':len(ownS),
        'force_minlot_N':0,'capital_score_replacement_N':0,'future_sell_used_before_BUY':False,
        'candidate_R_replay':{'status':'NOT_EXECUTED','reason':'All8 qualification blocks false'},
        'detail_artifact':'private/SHADOW_NATIVE_SNAPSHOT_PROBES.jsonl.gz','independent_detail_sha256':sha(p)})
    print(json.dumps({'status':'PASS','mismatch_N':0,'checks':sum(CHECKS.values()),'native_batch_N':len(proposals),'snapshot_N':len(records),'S_N':len(ownS),'past_table_N':len(own_tables),'qualified_N':audit['qualified_block_N']}))

if __name__=='__main__':main()
