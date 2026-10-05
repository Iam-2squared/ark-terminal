"""Independent integer/Decimal audit of saved money and derived tables.

Does not import anatomy, any market/EXIT engine, allocator or model code.
"""
from pathlib import Path
from collections import Counter
from decimal import Decimal, localcontext
from datetime import datetime
from zoneinfo import ZoneInfo
import csv, gzip, hashlib, json, math

REPO=Path(__file__).resolve().parents[2];ROOT=REPO.parent
OUT=REPO/'docs/evidence/capital-full-r-spectrum-20261006-v1'
OLD=REPO/'docs/evidence/capital-v51-reset20-r5r10-20261006-v1'
PRIVATE=ROOT/'capital_r_spectrum_private';PREVIOUS=ROOT/'capital_v51_private'
def read(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(s) for s in gzip.open(p,'rt') if s.strip()]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def decimal_pair(s):
    t=Decimal(s).as_tuple();n=int(''.join(map(str,t.digits)) or '0')*(-1 if t.sign else 1)
    return (n*10**t.exponent,1) if t.exponent>=0 else (n,10**(-t.exponent))
def return_pair(debit,credit):
    bn,bd=decimal_pair(debit);sn,sd=decimal_pair(credit)
    assert bn>0; n=sn*bd-bn*sd;d=sd*bn;g=math.gcd(n,d);return n//g,d//g
def classified(n,d,label):
    if label=='R0PLUS':return n>=0
    if label=='RPOS':return n>0
    if label=='ZERO':return n==0
    if label=='RNEG':return n<0
    if label=='Loser':return n<=0
    if label.startswith('RN'):return 100*n<=-int(label[2:])*d
    return 100*n>=int(label[1:])*d
def main():
    failures=[]; checks=Counter()
    def check(name,condition,context=None):
        checks[name]+=1
        if not condition:failures.append({'check':name,'context':context})
    original=rows(PREVIOUS/'evaluation-only/R_LABELS.jsonl.gz');derived=rows(PRIVATE/'evaluation-only/R_SPECTRUM_ROWS.jsonl.gz')
    meta=read(PRIVATE/'DERIVATION_COMPLETE.json'); lm={r['entry_id']:r for r in original};dm={r['entry_id']:r for r in derived}
    check('identity_one_to_one',len(lm)==len(original)==len(dm)==len(derived)==1039 and set(lm)==set(dm))
    check('source_hash',sha(PREVIOUS/'evaluation-only/R_LABELS.jsonl.gz')==meta['source_sha256'])
    check('contract_hash',sha(OUT/'R_SPECTRUM_CONTRACT.json')==meta['contract_sha256'])
    check('derived_hash',sha(PRIVATE/'evaluation-only/R_SPECTRUM_ROWS.jsonl.gz')==meta['output_sha256'])
    raw={}; unknown=0
    for identity,s in lm.items():
        r=dm[identity];ctx=hashlib.sha256(identity.encode()).hexdigest()
        for key in ['known','rank_pass','execution_eligible','U5','U10','rank','session','block','unknown_reason']:
            check('inherited_mask_and_U_flags',s[key]==r[key],ctx)
        if not s['known']:
            unknown+=1;check('unknown_excluded_from_events',r['realized_net_return_exact'] is None and r['bucket_pp_lower'] is None and all(x is None for x in r['events'].values()),ctx);continue
        n,d=return_pair(s['buy_debit'],s['sell_credit']);raw[identity]=(n,d)
        rn,rd=r['realized_net_return_exact']
        check('raw_money_continuous_R',n*rd==rn*d and n*s['r_net_fraction'][1]==s['r_net_fraction'][0]*d,ctx)
        check('exact_bucket_floor',r['bucket_pp_lower']==(100*n)//d,ctx)
        for label in meta['labels']:check('integer_boundary_event',r['events'][label]==classified(n,d,label),ctx)
        check('existing_R5_R10_Loser',r['events']['R5']==s['R5'] and r['events']['R10']==s['R10'] and r['events']['Loser']==s['Loser'],ctx)
    check('known_unknown_census',len(raw)==1016 and unknown==23)
    check('eligible_N',sum(r['execution_eligible'] for r in original)==1028)
    check('rankpass_N',sum(r['execution_eligible'] and r['rank_pass'] for r in original)==494)
    for prefix,maxk in [('R',37),('RN',17)]:
        for k in range(1,maxk+1):
            # Exact, immediately before and immediately after every observed grid threshold.
            boundary=(k if prefix=='R' else -k)*10**10;den=10**12
            for offset in [-1,0,1]:
                expected=offset>=0 if prefix=='R' else offset<=0
                check('synthetic_exact_boundary_triplets',classified(boundary+offset,den,f'{prefix}{k}')==expected)
    for n in [-1,0,1]:
        check('zero_RNEG_vs_Loser',classified(n,10**12,'RNEG')==(n<0) and classified(n,10**12,'Loser')==(n<=0))
    binding=read(OUT/'START_AND_SOURCE_BINDING.json');refs=binding['source_refs'];paths={k:Path(v['local_path']) for k,v in refs['inputs'].items()}
    decisions=rows(paths['native_decisions']);trades=rows(paths['native_trades']);native={r['entry_id']:r for r in decisions};funded={t['entry_id']:t for t in trades}
    check('native_trade_funded_identity',set(funded)=={k for k,v in native.items() if v['reason']=='FUNDED'} and len(funded)==150)
    for k,t in funded.items():
        c=hashlib.sha256(k.encode()).hexdigest(); n,d=return_pair(t['debit'],t['credit']);rn,rd=raw[k]
        check('funded_reference_return',n*rd==rn*d,c)
        check('funded_quantity',t['quantity']==native[k]['quantity'] and t['quantity']>=100 and t['quantity']%100==0,c)
        check('funded_money',Decimal(t['debit'])==Decimal(native[k]['debit'])==t['quantity']*Decimal(t['buy_effective']) and Decimal(t['credit'])==t['quantity']*Decimal(t['sell_effective']) and Decimal(t['credit'])-Decimal(t['debit'])==Decimal(t['pnl']),c)
        check('reference100_money',Decimal(lm[k]['buy_debit'])==100*Decimal(t['buy_effective']) and Decimal(lm[k]['sell_credit'])==100*Decimal(t['sell_effective']),c)
        check('funded_holding_and_release',t['release_minute']-t['entry_minute']==lm[k]['holding_minutes'] and t['release_minute']==lm[k]['release_minute'] and t['exit_kind']==lm[k]['exit_kind'],c)
        check('funded_slot_occupancy',native[k]['funded_slot'] in [1,2,3] and native[k]['funded_slot']==native[k]['pre_decision_occupancy']+1,c)
    pops={'ALL_FROZEN_ENTRY':list(lm),'EXECUTION_ELIGIBLE':[k for k,r in lm.items() if r['execution_eligible']],
          'RANK_PASS_EXECUTION_ELIGIBLE':[k for k,r in lm.items() if r['execution_eligible'] and r['rank_pass']],
          'V5_FUNDED':list(funded),'V5_NOT_FUNDED':[k for k in lm if k not in funded],
          'V5_RESERVE_REJECT':[k for k in lm if native[k]['reason']=='SLOT_RESERVE_REJECT'],
          'V5_MAX3_FULL':[k for k in lm if native[k]['reason']=='MAX_POSITION_CAP'],
          'V5_CASH_OR_LOT':[k for k in lm if native[k]['reason']=='CASH_OR_LOT_CONSTRAINED']}
    for reason in {r['reason'] for r in decisions}-{'FUNDED','SLOT_RESERVE_REJECT','MAX_POSITION_CAP','CASH_OR_LOT_CONSTRAINED'}:
        pops['NATIVE_REASON_'+reason]=[k for k in lm if native[k]['reason']==reason]
    census=read(OUT/'R_FULL_CENSUS.json')['populations']
    def audit_population(name,ids,z):
        known=[k for k in ids if k in raw];bins=Counter((100*raw[k][0])//raw[k][1] for k in known)
        check('population_counts',z['N']==len(ids) and z['known_N']==len(known) and z['unknown_N']==len(ids)-len(known),name)
        check('bucket_partition',sum(b['candidate_N'] for b in z['buckets'])==len(known),name)
        for b in z['buckets']:
            ids_in=[k for k in known if (100*raw[k][0])//raw[k][1]==b['bucket_pp_lower']]
            check('bucket_N',b['candidate_N']==bins[b['bucket_pp_lower']],name)
            check('bucket_funded_shares',b['funded_N']==sum(k in funded for k in ids_in) and b['funded_shares']==sum(funded[k]['quantity'] for k in ids_in if k in funded),name)
            check('bucket_miss_reason',b['miss_reason_N']==dict(Counter(native[k]['reason'] for k in ids_in if k not in funded)),name)
        cumulative={x['label']:x for x in z['cumulative']}
        for label,x in cumulative.items():
            event_ids=[k for k in known if classified(*raw[k],label)]
            check('cumulative_event_count',x['event_N']==len(event_ids) and x['known_N']==len(known),name+' '+label)
            check('cumulative_funded_missed',x['funded_N']==sum(k in funded for k in event_ids) and x['missed_N']==sum(k not in funded for k in event_ids),name+' '+label)
        for prefix in ['R','RN']:
            ordered=[cumulative[f'{prefix}{k}']['event_N'] for k in range(1,(37 if prefix=='R' else 17)+1)]
            check('cumulative_monotonic',all(a>=b for a,b in zip(ordered,ordered[1:])),name+' '+prefix)
        with localcontext() as context:
            context.prec=80;v=sorted(Decimal(raw[k][0])/Decimal(raw[k][1])*100 for k in known)
            if v:
                check('continuous_mean',abs(sum(v)/len(v)-Decimal(z['continuous_return']['mean']))<Decimal('1e-50'),name)
                for pct,display in z['continuous_return']['quantiles'].items():
                    p=(len(v)-1)*Decimal(pct)/100;i=int(p);q=v[i]+(p-i)*(v[min(i+1,len(v)-1)]-v[i])
                    check('continuous_quantile',abs(q-Decimal(display))<Decimal('1e-50'),name+' '+pct)
    for name,ids in pops.items():audit_population(name,ids,census[name])
    ug={'ALL_KNOWN_U5':[k for k,r in lm.items() if r['U5'] is True],
        'U5_NOT_U10':[k for k,r in lm.items() if r['U5'] is True and r['U10'] is False],
        'U10':[k for k,r in lm.items() if r['U10'] is True],'NON_U5':[k for k,r in lm.items() if r['U5'] is False],
        'U_UNKNOWN':[k for k,r in lm.items() if r['U5'] is None or r['U10'] is None]}
    cross=read(OUT/'U_R_CROSS.json')['groups']
    for name,ids in ug.items():audit_population(name,ids,cross[name])
    check('U_partition',sum(len(ug[k]) for k in ['U5_NOT_U10','U10','NON_U5','U_UNKNOWN'])==1039 and set(ug['U10'])<=set(ug['ALL_KNOWN_U5']))
    flow=read(OUT/'V5_R_CAPITAL_FLOW.json')
    def audit_flow(tt,source):
        debit=sum((Decimal(t['debit']) for t in tt),Decimal(0));credit=sum((Decimal(t['credit']) for t in tt),Decimal(0))
        check('flow_trade_shares',source['trade_N']==len(tt) and source['shares']==sum(t['quantity'] for t in tt))
        check('flow_money',Decimal(source['buy_debit_jpy'])==debit and Decimal(source['sell_credit_jpy'])==credit and Decimal(source['realized_pnl_jpy'])==credit-debit)
        check('flow_holding_capital_time',source['holding_minutes_total']==sum(t['release_minute']-t['entry_minute'] for t in tt) and Decimal(source['capital_minutes_jpy'])==sum((Decimal(t['debit'])*(t['release_minute']-t['entry_minute']) for t in tt),Decimal(0)))
    audit_flow(trades,flow['total'])
    for b in flow['buckets']:audit_flow([t for t in trades if (100*raw[t['entry_id']][0])//raw[t['entry_id']][1]==b['bucket_pp_lower']],b)
    for b in flow['cumulative']:audit_flow([t for t in trades if classified(*raw[t['entry_id']],b['label'])],b)
    check('original_R5_R10_capture',sum(classified(*raw[k],'R5') for k in funded)==19 and sum(classified(*raw[k],'R10') for k in funded)==11)
    reset=read(OUT/'RESET20_R_FLOW.json');saved={w['window_id']:w for w in read(OLD/'V5_RESET20_RESULT.json')['windows']}
    for w in reset['windows']:
        check('saved_reset_endpoint',w['final_cash_for_primary']==saved[w['window_id']]['final_cash_for_primary'] and w['status']==saved[w['window_id']]['status'])
        if w['R_flow'] is None:
            check('blocked_reset_null',w['status']=='BLOCKED_COVERAGE' and w['final_cash_for_primary'] is None);continue
        tt=rows(PREVIOUS/'runs/V5_RESET20'/w['window_id']/'TRADES.jsonl.gz');f=w['R_flow'];audit_flow(tt,f['total'])
        check('reset_final_cash',Decimal(w['final_cash_for_primary'])==Decimal(1000000)+sum((Decimal(t['credit'])-Decimal(t['debit']) for t in tt),Decimal(0)))
        for b in f['buckets']:audit_flow([t for t in tt if (100*raw[t['entry_id']][0])//raw[t['entry_id']][1]==b['bucket_pp_lower']],b)
        for b in f['cumulative']:audit_flow([t for t in tt if classified(*raw[t['entry_id']],b['label'])],b)
    score=read(OUT/'SCORE_R_SPECTRUM.json');sp=next(Path(v['local_path']) for v in refs['expert_score_sources'] if Path(v['local_path']).name=='c7e10944822c_CURRENT_MRET_CAP_RUNTIME.jsonl.gz');scores={s['entry_id']:s for s in rows(sp)}
    for curve in score['pooled']:
        ids=[k for k in pops[curve['population']] if k in raw];positive=sum(classified(*raw[k],curve['label']) for k in ids)
        check('score_mask_denominator',curve['N']==len(ids) and curve['positive_N']==positive and curve['negative_N']==len(ids)-positive)
    # Pairwise wins/ties is an independent path from the main grouped rank-sum AUROC.
    for head,column in score['heads'].items():
        for label in ['R1','RN1']:
            ids=pops['EXECUTION_ELIGIBLE'];yes=[scores[k][column] for k in ids if k in raw and classified(*raw[k],label)];no=[scores[k][column] for k in ids if k in raw and not classified(*raw[k],label)]
            twice=sum(2*(a>b)+(a==b) for a in yes for b in no);value=twice/(2*len(yes)*len(no))
            saved_auc=next(x['raw_direction_AUROC'] for x in score['pooled'] if x['population']=='EXECUTION_ELIGIBLE' and x['head']==head and x['label']==label)
            check('raw_score_direction_pairwise_AUROC',value==saved_auc,head+' '+label)
    check('no_score_inversion',score['direction']=='Original higher score, RN not inverted')
    result={'schema':'ARK_INDEPENDENT_FULL_R_AUDIT_V1','exact_jst':datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),
            'pass':not failures,'mismatch_N':len(failures),'mismatches':failures,'checks':dict(checks),'check_N':sum(checks.values()),
            'known_N':len(raw),'unknown_N':unknown,'original_funded_N':150,'saved_reset_complete_N':9,
            'method':'Independent integer monetary ratios/cross multiplication and Decimal quantiles; raw V5 trade sums; pairwise AUROC for all4 raw heads at symmetric R1/RN1. No main analytical functions, execution/EXIT engine or allocator imported.',
            'new_fits':0,'new_replays':0,'R_market_EXIT_rematerializations':0,'source_sha256':meta['source_sha256'],'derived_sha256':meta['output_sha256']}
    (OUT/'INDEPENDENT_R_AUDIT.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'pass':result['pass'],'mismatch_N':len(failures),'check_N':result['check_N'],'failures':failures[:5]}))
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
