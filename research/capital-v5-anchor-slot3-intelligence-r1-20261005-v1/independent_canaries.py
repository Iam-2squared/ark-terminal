"""R1 independent synthetic canaries; no actual market streams or teachers.

The counted market reconstruction entry point run_profile is never called.
Outcome-blind functions receive fictional fixtures. Embedded event-loop invariants
without a pure helper are verified structurally and explicitly marked as such.
Only separately implemented independent_engine/independent_metrics are imported.
"""
from __future__ import annotations
import ast
from copy import deepcopy
from decimal import Decimal as D
from fractions import Fraction as F
import hashlib
import inspect
import json
from pathlib import Path
from datetime import datetime, timezone

import independent_engine as e
import independent_metrics as m

DAY = 'SYNTHETIC_SESSION_00'
SOURCE = Path(e.__file__).read_text(encoding='utf-8')
TREE = ast.parse(SOURCE)
LOOP_SOURCE = inspect.getsource(e.run_profile)
RECORDS = []


def require(condition, message='independent synthetic assertion'):
    if not condition:
        raise AssertionError(message)


def record(number, name, function, mode='PURE_FUNCTION_SYNTHETIC'):
    try:
        evidence = function()
        RECORDS.append({'number': number, 'name': name, 'status': 'PASS', 'mode': mode,
                        'evidence': evidence if evidence is not None else 'Concrete assertions passed.'})
    except Exception as problem:
        RECORDS.append({'number': number, 'name': name, 'status': 'FAIL', 'mode': mode,
                        'error': f'{type(problem).__name__}: {problem}'})


def candidate(identity, ml=2.0, price='100', symbol=None, minute=600):
    rank = 'S' if ml >= 2 else 'A' if ml >= 1.5 else 'B' if ml >= 1 else 'C'
    return {'entry_id': identity, 'session': DAY, 'entry_minute': minute,
            'entry_timestamp': f'2000-01-01T{minute//60:02d}:{minute%60:02d}:00+09:00',
            'symbol': symbol or identity, 'ML': ml, 'capital_score': ml,
            'm2': .8, 'm3': .6, 'm5': .4, 'rank': rank, 'capacity_band': rank,
            'admission': ml >= 1, 'block': 1, 'raw_reference': price}


def tables(probability=.1, expected=.1, median=1.1, p75=1.2):
    n = 100
    return {'1': {'training_session_N': n, 'B_median': median, 'B_p75': p75,
                  'minute_counts': {str(t): [int(probability*n), 0, int(expected*n)] for t in range(540, 921)},
                  'minute_bucket': {str(t): t//30*30 for t in range(540, 921)}}}


def held(number=2):
    return {f'h{i+1}': {'symbol': f'HOLD{i+1}', 'quantity': 100,
                         'mark': '100', 'band': 'S'} for i in range(number)}


def axis(current=0.0, reference=(.1, .2, .3)):
    return {'score': current, 'training_scores': list(reference)}


def intel(ids, high=False):
    return {identity: {head: axis(.4 if high else 0.) for head in e.HEADS} for identity in ids}


def snapshot(rows, existing=0, cash=None, minute=600):
    return {'session': DAY, 'minute': minute, 'cash': cash or str(1000000-10000*existing),
            'positions': held(existing), 'candidates': rows}


def token():
    return {'session': DAY, 'created_minute': 600, 'origin_entry_id': 'veto_origin',
            'held_pair_ids': ['h1', 'h2'], 'active': True}


def reserve_decisions(rows, reason='SLOT3_RESERVE_FOR_FUTURE_QUALITY'):
    return [{'entry_id': r['entry_id'], 'slot_gate_reason': reason} for r in rows]


def recovery(rows=None, intelligence=None, **overrides):
    rows = rows or [candidate('winner', 1.3, minute=601)]
    args = dict(token=token(), day=DAY, minute=601, positions=held(),
                native_picked_ids=[], rows=rows, decisions=reserve_decisions(rows),
                intelligence=intelligence or intel([r['entry_id'] for r in rows], True))
    args.update(overrides)
    return e.recovery_choices(**args)


def synthetic_current(existing):
    rows = [candidate(f'new{i+1}') for i in range(3-existing)]
    output = e.reconstruct_batch(snapshot(rows, existing), tables(), intel([r['entry_id'] for r in rows]))
    return rows, output


def sc01(existing):
    rows, output = synthetic_current(existing)
    ds = output['decisions']
    require(ds[-1]['slot_admission_index'] == 3)
    require(ds[-1]['actual_planned_slot'] == 3)
    require(ds[-1]['prior_native_successful_BUY_proposal_N'] == 2-existing)
    require(ds[-1]['D_veto'])
    expected = ([2600,2600,2600], [3900,3800], [4400])[existing]
    require([d['native_quantity'] for d in ds] == expected,
            'Hand-calculated simultaneous allocation quantities')
    return {'existing': existing, 'prior_successful': 2-existing, 'planned_slot': 3,
            'expected_quantity': expected}


for number, existing in ((1,0),(2,1),(3,2)):
    record(number, f'SC01 existing{existing} actual planned3 unanimousLOW veto', lambda existing=existing: sc01(existing))


def no_veto_for_actual(existing):
    row = candidate('only')
    result = e.reconstruct_batch(snapshot([row], existing), tables(), intel(['only']))['decisions'][0]
    require(result['actual_planned_slot'] == existing+1 and result['D_veto'] is False)
    return {'actual_planned_slot': result['actual_planned_slot']}
record(4, 'SC01 existing0 actual planned1 no veto', lambda: no_veto_for_actual(0))
record(5, 'SC01 existing1 actual planned2 no veto', lambda: no_veto_for_actual(1))


def prior_cash_fail():
    rows = [candidate('too_expensive', 2.3, '10000'), candidate('second',2.2),candidate('third',2.1)]
    result = e.reconstruct_batch(snapshot(rows),tables(),intel([r['entry_id'] for r in rows]))
    ds = result['decisions']
    require(ds[0]['native_quantity']==0)
    require(ds[2]['slot_admission_index']==3 and ds[2]['actual_planned_slot']==2)
    require(ds[2]['prior_native_successful_BUY_proposal_N']==1 and not ds[2]['D_veto'])
    require(sum(x['native_quantity'] for x in ds)==7800)
    return {'native_index':3,'actual_planned_slot':2,'first_quantity':0,'total_quantity':7800}
record(6,'Native index3 prior cash/lot failure makes actual planned2 no veto',prior_cash_fail)


def exact_half():
    result=e.empirical_rank(.5,[.5])
    require(result['numerator']==1 and result['denominator']==2 and result['high'] and not result['low'])
    return result
record(7,'SC02 exact 1/2 HIGH',exact_half)


def median_equal_low():
    result=e.empirical_rank(.5,[.1,.5,.5,.9])
    require(result['numerator']==2 and result['denominator']==5 and result['low'])
    return result
record(8,'SC02 raw median equality rank2/5 LOW',median_equal_low)


def strict_ties():
    result=e.empirical_rank(.5,[.5,.5,.5])
    require(result['numerator']==1 and result['denominator']==4 and result['low'])
    return result
record(9,'SC02 strict-less ties',strict_ties)


def one_high():
    values=intel(['new1']);values['new1']['pP']=axis(.4)
    state=e.intelligence_state('new1',values)
    require(state['HIGH_P'] and not e.shield('ADMIT',3,3,100,state))
    return {'LOW_count':sum(state['LOW_'+name[1:]] for name in e.RANK_NAMES.values()),'veto':False}
record(10,'One HIGH disables unanimous LOW shield',one_high)


def unavailable(value):
    values=intel(['new1']);values['new1']['pP']=axis(value)
    state=e.intelligence_state('new1',values)
    require(not state['intelligence_available'] and state['LOW_P'] is None)
    require(not e.shield('ADMIT',3,3,100,state))
    return {'intelligence_available':False,'LOW':None,'veto':False}
record(11,'Missing score abstains to V5',lambda:unavailable(None))
record(12,'Nonfinite score abstains to V5',lambda:[unavailable(v) for v in (float('nan'),float('inf'),float('-inf'))])


def test_reference_exclusion():
    fictional=[{'session':'PAST01','score':.1},{'session':'PAST02','score':.2},
               {'session':'TEST00','score':999.0},{'session':'FUTURE','score':-999.0}]
    completed={'PAST01','PAST02'}
    assemble=lambda rows:[r['score'] for r in rows if r['session'] in completed]
    before=e.empirical_rank(.1,assemble(fictional))
    after=e.empirical_rank(.1,assemble([r for r in fictional if r['session'] in completed]))
    require(before==after and before['denominator']==3)
    return {'reference_N':2,'test_future_reference_N':0,'rank_exact':'1/3',
            'scope':'Synthetic training-identity assembly plus empirical_rank; frozen real training coverage audited separately.'}
record(13,'Remove heldout test rows leaves completed-past reference/action unchanged',test_reference_exclusion)


def forbidden_mutation(field):
    rows=[candidate('new1')]
    values=intel(['new1'])
    original=e.reconstruct_batch(snapshot(rows,2),tables(),values)
    changed=deepcopy(rows);changed[0][field]={'changed':True,'future_known_at':999}
    changed_values=deepcopy(values);changed_values['new1'][field]={'arbitrary_future':True}
    altered=e.reconstruct_batch(snapshot(changed,2),tables(),changed_values)
    require(altered==original)
    return {'mutated_field':field,'decision_unchanged':True}
record(14,'Future High mutation does not affect action',lambda:forbidden_mutation('future_High'))
record(15,'Future realized mutation does not affect action',lambda:forbidden_mutation('future_realized_pnl'))
record(16,'Future EXIT mutation does not affect action',lambda:forbidden_mutation('future_EXIT'))


def same_batch_quantities():
    rows=[candidate(f'new{i}') for i in range(3)]
    low=e.reconstruct_batch(snapshot(rows),tables(),intel([r['entry_id'] for r in rows]))
    high=e.reconstruct_batch(snapshot(rows),tables(),intel([r['entry_id'] for r in rows],True))
    require(low['assigned']==high['assigned'])
    require([a['quantity'] for a in low['assigned']]==[2600,2600,2600])
    require([D(a['debit']) for a in low['assigned']]==[D('260130')]*3)
    require([d['D_veto'] for d in low['decisions']]==[False,False,True])
    return {'quantities':[2600,2600,2600],'debits':['260130']*3,'assigned_before_veto':True}
record(17,'Other native quantities and exact debits unchanged',same_batch_quantities)


def structure_fragments(fragments):
    for fragment in fragments:
        require(fragment in LOOP_SOURCE,f'Absent structural contract fragment: {fragment}')
    return {'verified_source_fragments':fragments,'runtime_eventloop_calls':0}
record(18,'No post-veto extra water-fill',lambda:structure_fragments([
    'assignment = {k: D(v)', 'if decision["D_veto"]:', 'veto_ids.append(key)', 'continue',
    'fund(row, decision, assignment, minute)']), 'STRUCTURAL_EVENTLOOP_SOURCE')


def no_native_backfill():
    source=inspect.getsource(e.reconstruct_batch)
    require(source.count('assigned = allocate(')==1)
    require('zip(picked, assigned)' in source and 'picked.append((row, decision))' in source)
    require('picked.append' not in source[source.index('prior = 0'):])
    return {'allocation_calls':1,'postallocation_admission_append_N':0}
record(19,'Native no backfill after veto or cash/lot failure',no_native_backfill,'STRUCTURAL_PURE_FUNCTION_SOURCE')
record(20,'Same-minute recovery prohibited',lambda:require(recovery(minute=600)==[]))


def maxone_token():
    return structure_fragments(['blockers, token, peak, cash_min = [], None, 0, opening',
                                'if token is None:', 'token = {"session": day',
                                'token["active"] = False','token = None'])
record(21,'At most one active token in embedded loop',maxone_token,'STRUCTURAL_EVENTLOOP_SOURCE')
record(22,'Held pair change invalidates',lambda:require(e.invalidate_token(token(),DAY,601,{'h1':held()['h1'],'h3':held()['h2']})=='HELD_PAIR_CHANGED'))
record(23,'Open less than2 invalidates',lambda:require(e.invalidate_token(token(),DAY,601,held(1))=='OPEN_BELOW_TWO'))
record(24,'Successful third BUY invalidates',lambda:require(e.invalidate_token(token(),DAY,601,held(3))=='THIRD_BUY_SUCCESS'))
record(25,'Cutoff invalidates',lambda:require(e.invalidate_token(token(),DAY,920,held())=='CUTOFF'))
record(26,'Session end invalidates',lambda:[require(e.invalidate_token(token(),DAY,601,held(),True)=='SESSION_END'),require(e.invalidate_token(token(),'NEXT',601,held())=='SESSION_CHANGED')])
record(27,'Old vetoed Entry retry prohibited',lambda:require(recovery(rows=[candidate('veto_origin',1.3,minute=601)])==[]))
record(28,'Nonempty native picked list disables recovery',lambda:require(recovery(native_picked_ids=['cashfail_native'])==[]))
record(29,'Only exact reserve reason admits recovery',lambda:require(recovery(decisions=reserve_decisions([candidate('winner',1.3)],'SLOT2_RESERVE_FOR_FUTURE_QUALITY'))==[]))
record(30,'Non-B candidate cannot recover',lambda:require(recovery(rows=[candidate('winner',1.5,minute=601)])==[]))
record(31,'Four HIGH axes required for recovery',lambda:require(recovery(intelligence=intel(['winner'],False))==[]))


def priority():
    ids=['priority_P','priority_U3','priority_M','priority_U2','stable_first','stable_second']
    rows=[candidate(x,1.1+i*.01,minute=601) for i,x in enumerate(ids)]
    # tuple order is rP, r3, rM, r2. All selected ranks have exact denominator10.
    ranks=[(.9,.5,.5,.5),(.8,.9,.5,.5),(.8,.8,.9,.5),(.8,.8,.8,.9),(.8,.8,.8,.8),(.8,.8,.8,.8)]
    values={}
    for identity, rr in zip(ids,ranks):
        values[identity]={head:axis(score-.05,tuple(j/10 for j in range(1,10)))
                          for head,score in zip(('pP','MOVE_U3','MRET','MOVE_U2'),rr)}
    selected=recovery(rows,values)
    ordered=[item[0]['entry_id'] for item in selected]
    # stable_second has higher native ML and wins the final exact-rank tie.
    expected=['priority_P','priority_U3','priority_M','priority_U2','stable_second','stable_first']
    require(ordered==expected)
    return {'expected_priority':expected,'rank_comparison':'Fraction exact'}
record(32,'Multiple recovery candidates exact lexicographic priority',priority)


def first_failure_no_second():
    rows=[candidate('first_high',1.1,'10000',minute=601),candidate('second_lower',1.4,'100',minute=601)]
    values=intel(['first_high','second_lower'],True)
    values['first_high']['pP']=axis(.9)
    values['second_lower']['pP']=axis(.2)
    selected=recovery(rows,values)
    require(selected[0][0]['entry_id']=='first_high')
    first=e.allocate([selected[0][0]],D('1000000'),D('100000'),D('900000'),['S','S'])[0]
    second=e.allocate([rows[1]],D('1000000'),D('100000'),D('900000'),['S','S'])[0]
    require(first['quantity']==0 and second['quantity']==2400)
    require('row, decision, state, _ = choices[0]' in LOOP_SOURCE)
    segment=LOOP_SOURCE[LOOP_SOURCE.index('if choices:'):LOOP_SOURCE.index('if minute == 920:')]
    require(segment.count('fund(row, decision, one, minute, True)')==1 and not any(isinstance(node,(ast.For,ast.While)) for node in ast.walk(ast.parse(segment))))
    return {'first_quantity':0,'second_counterfactual_quantity':2400,'attempt_index':0,'second_attempt_N':0}
record(33,'First eligible cash/lot failure does not backfill second',first_failure_no_second,'PURE_FUNCTION_PLUS_STRUCTURAL_EVENTLOOP')


def singleton_exact():
    out=e.allocate([candidate('singleton',1.1)],D('1000000'),D('100000'),D('900000'),['S','S'])[0]
    require(out['target_utilization']==D('.79') and out['batch_budget']==D('690000'))
    require(out['equity_cap']==D('250000') and out['quantity']==2400 and out['debit']==D('240120'))
    require(out['budget_unspent']==D('449880'))
    return {'target':'.79','budget':'690000','B_cap':'250000','quantity':2400,'debit':'240120'}
record(34,'Recovery singleton allocation hand-calculated exact',singleton_exact)


def max3():
    out=e.reconstruct_batch(snapshot([candidate('extra')],3),tables(),intel(['extra']))
    require(out['picked_ids']==[] and out['decisions'][0]['reason']=='MAX_POSITION_CAP')
    require('assert len(positions) <= 3' in LOOP_SOURCE)
    return {'existing':3,'extra_admission':False}
record(35,'MAX3 bound enforced',max3)


def same_symbol():
    out=e.reconstruct_batch(snapshot([candidate('duplicate',symbol='HOLD1')],1),tables(),intel(['duplicate']))
    require(out['picked_ids']==[] and out['decisions'][0]['reason']=='SYMBOL_ALREADY_OPEN')
    require('assert len({p["symbol"] for p in positions.values()}) == len(positions)' in LOOP_SOURCE)
    return {'held_symbol_duplicate_rejected':True,'funded_unique_assertion':True}
record(36,'Same symbol at most one held position',same_symbol)
record(37,'Lot100 quantity contract',lambda:require(e.allocate([candidate('lot')],D('1000000'),0,D('1000000'),[])[0]['quantity']==4400))


def buy_exact():
    require(e.BUY==D('1.0005'))
    out=e.allocate([candidate('buy')],D('1000000'),0,D('1000000'),[])[0]
    require(out['lot_debit']==D('10005') and out['debit']==D('440220'))
    require(D('100')*e.BUY*4400==out['debit'])
    return {'raw':'100','effective':'100.0500','quantity':4400,'debit':'440220'}
record(38,'BUY coefficient exact',buy_exact)


def market(minute=601,session=DAY,raw='100',auction=False):
    return {'session':session,'minute':minute,'O':raw,'H':raw if auction else str(D(raw)+1),
            'L':raw if auction else str(D(raw)-1),'C':raw,'Vo':'100','Va':str(D(raw)*100),
            'lineage':'SYNTHETIC_LINEAGE'}


def book():
    return {'frozen_exit':{'sell_status':'FILLED','sell_source_assumed_available_at':'2000-01-01T10:02:00+09:00',
            'sell_minute':601,'sell_source':'NEXT_ELIGIBLE_REGULAR_RAW_OPEN','sell_price_decimal':'99.9500'},
            'market':[market()]}


def sell_exact():
    require(e.SELL==D('.9995'))
    out=e.frozen_sell(book())
    require(D(out['price'])==D('99.95') and out['source_minute']==601 and out['release_minute']==602)
    close=e.closing_sell({'market':[market(920),market(930,auction=True)]},DAY)
    require(close['kind']=='EOD_REGULAR' and close['release_minute']==921 and D(close['price'])==D('99.95'))
    auction=e.closing_sell({'market':[market(930,auction=True)]},DAY)
    require(auction['kind']=='EOD_EXACT_1530_AUCTION' and auction['release_minute']==931)
    return {'SELL_effective':'99.95','frozen_release':602,'regular_release':921,'auction_release':931}
record(39,'SELL frozen and EOD coefficients exact',sell_exact)


def mtm_exact():
    debit=D('260130');cash=D('1000000')-debit;q=2600
    require(cash+q*D('100')==D('999870'))
    require(cash+q*D('110')==D('1025870'))
    require('r["minute"] + 1, D(r["C"])' in LOOP_SOURCE)
    require('p["mark_updates"][p["mark_index"]][0] <= minute' in LOOP_SOURCE)
    require('eq = cash + sum(p["quantity"] * p["mark"] for p in positions.values())' in LOOP_SOURCE)
    return {'entry_MTM':'999870','next_known_close_MTM':'1025870','availability':'source_minute+1'}
record(40,'MTM exact arithmetic and close availability',mtm_exact,'SYNTHETIC_ARITHMETIC_PLUS_STRUCTURAL_EVENTLOOP')


def cash_release():
    fill=e.frozen_sell(book())
    require(fill['release_minute']==602)
    before=D('90000');after=before+D(fill['price'])*100
    require(before==D('90000') and after==D('99995'))
    require(LOOP_SOURCE.index('scheduled.pop(minute, [])')<LOOP_SOURCE.index('proposed = reconstruct_batch'))
    return {'source_minute':601,'available_minute':602,'cash_before':'90000','cash_after':'99995','release_before_entry_batch':True}
record(41,'Cash release at exact availability and before same-minute entries',cash_release,'PURE_FUNCTION_PLUS_STRUCTURAL_EVENTLOOP')


def cutoff():
    before=e.reconstruct_batch(snapshot([candidate('before',minute=919)],minute=919),tables(),intel(['before']))
    at=e.reconstruct_batch(snapshot([candidate('at',minute=920)],minute=920),tables(),intel(['at']))
    require(before['decisions'][0]['native_quantity']==4400)
    require(at['picked_ids']==[] and at['decisions'][0]['reason']=='CAPITAL_EOD_ENTRY_CUTOFF')
    return {'919_admitted':True,'920_admitted':False}
record(42,'15:20 cutoff exact',cutoff)


def protected_only_eval():
    pure_sources='\n'.join(inspect.getsource(getattr(e,name)) for name in
        ('reconstruct_batch','native_gate','allocate','empirical_rank','shield','recovery_choices','invalidate_token'))
    pure_ast=ast.parse(pure_sources)
    policy_literals=[node.value for node in ast.walk(pure_ast) if isinstance(node,ast.Constant) and isinstance(node.value,str) and '\n' not in node.value]
    require(not any('protected' in value or 'teacher' in value for value in policy_literals))
    rows=[candidate('free')];prior=e.reconstruct_batch(snapshot(rows,2),tables(),intel(['free']))
    changed=snapshot(rows,2);changed['protected_slot12_membership']=['free'];changed['teacher_potential']=.99
    require(e.reconstruct_batch(changed,tables(),intel(['free']))==prior)
    require('protectedSlot12' in inspect.getsource(m.quality))
    return {'policy_protected_reads':0,'protected_membership_evaluator_only':True}
record(43,'Protected100 evaluation-only dependency',protected_only_eval)


def fake_quality_input():
    decisions=[];trades=[];baseline=[];teachers=[]
    for i in range(150):
        identity=f'SYNTHETIC_TRADE_{i:03d}'
        decisions.append({'entry_id':identity,'quantity':100,'funded_slot':1 if i<41 else 2 if i<100 else 3})
        bp=-1 if i<82 else 1;cp=1 if i==81 else bp
        trades.append({'entry_id':identity,'pnl':str(cp)})
        baseline.append({'entry_id':identity,'pnl':str(bp)})
        potential='.10' if i<26 else '.05' if i<50 else '.03' if i<77 else '.01' if i<135 else '.02'
        teachers.append({'entry_id':identity,'potential_return':potential})
    return decisions,trades,baseline,teachers


FAKE_DECISIONS,FAKE_TRADES,FAKE_BASELINE_TRADES,FAKE_TEACHERS=fake_quality_input()
QUALITY=m.quality(FAKE_DECISIONS,FAKE_TRADES,FAKE_TEACHERS,FAKE_DECISIONS,FAKE_BASELINE_TRADES)


def denominator():
    require(QUALITY['denominator']==150 and m.exact(QUALITY['rate']['Weak'])==F(58,150))
    require(m.exact(QUALITY['rate']['loser_le_zero'])==F(81,150))
    require(QUALITY['count']['U5']==50 and QUALITY['count']['U10']==26 and QUALITY['count']['Medium']==27)
    require(QUALITY['protectedSlot12']['1']['group_N']==41 and QUALITY['protectedSlot12']['2']['group_N']==59)
    return {'funded_BUY_denominator':150,'Weak':'58/150','loser_le_zero':'81/150','protected':100}
record(44,'Q rates denominator funded BUY N and exact boundaries',denominator)


def fake_capital(changes):
    before=1000000;daily=[];curves=[]
    for index,delta in enumerate(changes):
        day=f'SYNTHETIC_SESSION_{index:02d}';after=before+delta
        daily.append({'session':day,'status':'COMPLETE','primary_chain':True,'starting_cash':str(before),
                      'ending_cash':str(after),'blockers':[],'open_obligations':[]})
        for point in range(392):
            curves.append({'session':day,'primary_chain':True,'minute':540+point,
                           'equity':F(before*392+delta*(point+1),392)})
        before=after
    return daily,curves


CAND_DAILY,CAND_CURVES=fake_capital([1000]*38)
BASE_DAILY,BASE_CURVES=fake_capital([0]*38)
CAND_CAPITAL=m.capital(CAND_DAILY,CAND_CURVES)
BASE_CAPITAL=m.capital(BASE_DAILY,BASE_CURVES)


def window_ids():
    windows=CAND_CAPITAL['windows']
    expected=[(f'SYNTHETIC_SESSION_{i:02d}',f'SYNTHETIC_SESSION_{i+19:02d}') for i in range(19)]
    require([(w['start_session'],w['end_session']) for w in windows]==expected)
    require(all(w['point_N']==7840 for w in windows))
    return {'window_N':19,'first':expected[0],'last':expected[-1],'points_per_window':7840}
record(45,'Exact 19 rolling20 window identities',window_ids)


def paired_noninferiority():
    diffs=[m.exact(a['growth'])-m.exact(b['growth']) for a,b in zip(CAND_CAPITAL['windows'],BASE_CAPITAL['windows'])]
    require(all(d>0 for d in diffs))
    losses=[1000]*38;losses[10]=-20000
    daily,curve=fake_capital(losses)
    worse=m.capital(daily,curve)
    deltas=[m.exact(a['growth'])-m.exact(b['growth']) for a,b in zip(worse['windows'],BASE_CAPITAL['windows'])]
    require(deltas[0]==F(-1,1000) and sum(d<0 for d in deltas)==11)
    require(not all(d>=0 for d in deltas))
    return {'positive_case_better':19,'loss_case_worse':11,'first_loss_paired_delta':'-1/1000'}
record(46,'Exact paired19 noninferiority detects one-window violation',paired_noninferiority)


def no_window_reset():
    require(CAND_DAILY[18]['starting_cash']=='1018000')
    require(m.exact(CAND_CAPITAL['windows'][18]['growth'])==F(519,509))
    require(m.exact(CAND_CAPITAL['windows'][18]['amount_from_1m'])==1000000*F(519,509))
    require(m.exact(CAND_CAPITAL['final38_equity_secondary_only'])==F(1038000))
    return {'window18_chain_start':'1018000','window18_growth':'519/509','final38_secondary':'1038000'}
record(47,'Rolling window uses continuous bankroll and no reset',no_window_reset)


def exact_gates():
    tiny='0.5000000000000000000000000001'
    require(float(tiny)==.5 and m.exact(tiny)>F(1,2))
    require(m.exact(m.pack(tiny))==m.exact(tiny))
    require(m.drawdown([{'equity':'120'},{'equity':'90'},{'equity':'110'}],'100')==F(1,4))
    candidate_output={'daily':CAND_DAILY,'curves':CAND_CURVES,'decisions':FAKE_DECISIONS,'trades':FAKE_TRADES}
    baseline_output={'daily':BASE_DAILY,'curves':BASE_CURVES,'decisions':FAKE_DECISIONS,'trades':FAKE_BASELINE_TRADES}
    evaluated=m.evaluate(candidate_output,baseline_output,FAKE_TEACHERS,0,True)
    require(evaluated['eligible'] and all(evaluated['gates'].values()))
    require(evaluated['paired19']['better']==19 and evaluated['paired19']['worse']==0)
    require(evaluated['gates']['Q1'] and evaluated['gates']['Q2'] and evaluated['gates']['Q3'])
    require(evaluated['gates']['Q4'] and evaluated['gates']['Q5'])
    incomplete=deepcopy(CAND_DAILY);incomplete[3]['status']='PORTFOLIO_MEASUREMENT_BLOCKED_EXECUTION'
    require(m.capital(incomplete,CAND_CURVES)=={'status':'NOT_EVALUATED'})
    return {'convenience_float_loses_tiny_delta':True,'exact_drawdown':'1/4','fictional_all_gates_PASS':True,
            'Q_boundaries':{'U5':50,'U10':26,'Medium':27,'Weak':58,'below3':73,'loser_le_zero':81},
            'incomplete_chain':'NOT_EVALUATED'}
record(48,'Decimal/Fraction metrics and economic/quality gate boundaries',exact_gates)


def safety_false():
    transmitted=[]
    for node in ast.walk(TREE):
        if isinstance(node,ast.Dict):
            for key,value in zip(node.keys,node.values):
                if isinstance(key,ast.Constant) and key.value=='transmitted':
                    transmitted.append(isinstance(value,ast.Constant) and value.value is False)
    require(transmitted and all(transmitted))
    calls=[node.func.attr for node in ast.walk(TREE) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)]
    require('fit' not in calls and 'partial_fit' not in calls)
    imports=[]
    for node in ast.walk(TREE):
        if isinstance(node,ast.Import):imports.extend(a.name for a in node.names)
        elif isinstance(node,ast.ImportFrom):imports.append(node.module)
    require(not any(x in imports for x in ('requests','subprocess','socket','httpx')))
    require('"commission": 0' in LOOP_SOURCE)
    return {'transmitted_fields_all_false':True,'trainer_calls':0,'provider_or_order_transport_imports':0,
            'scope':'Independent engine transport/fit invariants; project Safety object certified by parent.'}
record(49,'Safety no live transport/fit/commission',safety_false,'STRUCTURAL_EVENTLOOP_AST')

# Extra immutable boundary cases complement the minimum 49 without any tuning.

def native_boundaries():
    row=candidate('B',1.2)
    tab=tables(probability=.5)['1']
    require(not e.native_gate(row,1,839,tab)[0] and e.native_gate(row,1,840,tab)[0])
    tab=tables(probability=.35,expected=.74)['1']
    require(not e.native_gate(row,2,869,tab)[0] and e.native_gate(row,2,870,tab)[0])
    tab=tables(probability=.34,expected=.75)['1']
    require(not e.native_gate(row,2,869,tab)[0])
    tab=tables(probability=.34,expected=.74)['1']
    require(e.native_gate(row,2,869,tab)[0])
    low=candidate('Blow',1.19)
    require(not e.native_gate(low,2,870,tab)[0])
    return {'slot2_probability50_strict':True,'slot3_probability35_strict':True,
            'slot3_expected75_strict':True,'late_release_times':[840,870],'late_quality_not_bypassed':True}
record(50,'Frozen native probability/time/quality exact boundaries',native_boundaries)


def finite_sources():
    for value in ('NaN','Infinity','-Infinity','0','-1'):
        row=market();row['O']=value
        require(e.valid_market(row) is False)
    row=market();del row['O'];require(e.valid_market(row) is False)
    row=market();row['lineage']=None;require(e.valid_market(row) is False)
    row=market(930);require(e.valid_market(row,True) is False)
    require(e.closing_sell({'market':[market(925)]},DAY) is None)
    require(e.closing_sell({'market':[market(920,session='OTHER')]},DAY) is None)
    return {'missingkeys_nonfinite_nonpositive_rejected':True,'invalid_auction_rejected':True,'minute925_not_regular':True,
            'malformed_numeric_string_or_None':'NOT_SUPPORTED_BY_FROZEN_CONTRACT; unchanged Decimal InvalidOperation behavior'}
record(51,'Frozen source validity and EOD unavailable boundaries',finite_sources)


if __name__=='__main__':
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    failed=[record for record in RECORDS if record['status']!='PASS']
    imports=[]
    syntax=ast.parse(Path(__file__).read_text())
    for node in ast.walk(syntax):
        if isinstance(node,ast.Import):imports.extend(a.name for a in node.names)
        elif isinstance(node,ast.ImportFrom):imports.append(node.module)
    report={'schema':'ARK_R1_INDEPENDENT_SYNTHETIC_CANARIES_V1','UTC':datetime.now(timezone.utc).isoformat(),
            'status':'PASS' if not failed else 'FAIL','case_N':len(RECORDS),'mandatory_N':49,
            'PASS_N':len(RECORDS)-len(failed),'FAIL_N':len(failed),'cases':RECORDS,
            'mode_counts':{mode:sum(case['mode']==mode for case in RECORDS) for mode in sorted({x['mode'] for x in RECORDS})},
            'primary_adapter_policy_replay_metrics_import_N':0,'imports':imports,
            'actual_market_input_N':0,'actual_teacher_input_N':0,'actual_PnL_input_N':0,
            'market_replay':0,'run_profile_calls':0,'new_fit':0,'performance_gate_on_actual_market':0,
            'fictional_metric_fixture':{'daily_N':38,'curve_points_per_day':392,'funded_BUY_N':150,'protectedSlot1_N':41,'protectedSlot2_N':59},
            'limitations':['Embedded event-loop invariants without pure helpers use explicit AST/source proofs; no synthetic or real event-loop replay was called.',
                           'Test-row reference exclusion uses fictional completed-past identities. Real frozen model/training/raw coverage is a separate independent audit.',
                           'Malformed textual or None Decimal price preserves frozen-contract InvalidOperation behavior and is not a newly supported source operator.'],
            'source_hashes':{'independent_engine':sha(e.__file__),'independent_metrics':sha(m.__file__),'independent_canaries':sha(__file__)}}
    path=Path('r1_work/independent/INDEPENDENT_SYNTHETIC_CANARIES_A2.json');assert not path.exists(), 'Append-only canary report already exists';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,sort_keys=True,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'case_N':report['case_N'],'PASS_N':report['PASS_N'],'FAIL_N':report['FAIL_N'],'failed':failed},sort_keys=True,default=str))
    raise SystemExit(bool(failed))
