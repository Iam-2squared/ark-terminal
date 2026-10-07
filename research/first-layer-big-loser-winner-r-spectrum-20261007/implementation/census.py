"""Saved-outcome descriptive census only. No model, score, threshold, or policy execution."""
import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
from pathlib import Path

POINTS = {'CAL95': 'CAL95', 'M80': 'CAL_MINUS_KEEP_80', 'M60': 'CAL_MINUS_KEEP_60',
          'M40': 'CAL_MINUS_KEEP_40', 'M20': 'CAL_MINUS_KEEP_20', 'M10': 'CAL_MINUS_KEEP_10'}
BANDS = ['L5_PLUS','L4_5','L3_4','L2_3','L1_2','L0_1','ZERO',
         'P0_1','P1_2','P2_3','P3_4','P4_5','P5_PLUS','R_UNKNOWN']
LABELS = 'LEGACY_DIAGNOSTIC_ONLY / NEGATIVE_EVIDENCE / NOT_A_NEW_PARENT'

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def gzrows(path):
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        return [json.loads(x) for x in f if x.strip()]

def dump(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def exact(value):
    if value is None:
        return 'N/A'
    if not isinstance(value, Fraction):
        value = Fraction(value)
    with localcontext() as c:
        c.prec = 240
        return format(Decimal(value.numerator) / Decimal(value.denominator), 'f')

def rate(a, b):
    if b == 0:
        return 'N/A'
    with localcontext() as c:
        c.prec = 240
        return format((Decimal(str(a)) / Decimal(str(b)) * 100).quantize(Decimal('0.000000000001')), 'f')

def massrate(a, b):
    if not b:
        return 'N/A'
    return rate((a / b * 100).numerator, (a / b * 100).denominator * 100)

def csvwrite(path, rows):
    with Path(path).open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def primary_R(row):
    if not row.get('return_available'):
        return None, 'FORMAL_R_UNAVAILABLE_SOURCE_REASON_UNSPECIFIED'
    token = row.get('R_native_fraction_decimal')
    if token is None:
        return None, 'NULL_R_NATIVE'
    try:
        native = Decimal(str(token))
    except InvalidOperation:
        return None, 'INVALID_R_NATIVE'
    if native.is_nan():
        return None, 'NAN_R_NATIVE'
    if not native.is_finite():
        return None, 'NONFINITE_R_NATIVE'
    if row.get('R_pct_numerator') is None or row.get('R_pct_denominator') is None:
        return None, 'NULL_R_CANONICAL_RATIO'
    try:
        pct = Fraction(int(row['R_pct_numerator']), int(row['R_pct_denominator']))
    except (ValueError, ZeroDivisionError, TypeError):
        return None, 'INVALID_R_CANONICAL_RATIO'
    assert row['R_unit'] == 'percent', 'R_UNIT_MISMATCH'
    assert pct == Fraction(native) * 100, 'SAVED_UNIT_CONVERSION_MISMATCH'
    assert row['sign_status'] == ('PLUS' if pct > 0 else 'MINUS' if pct < 0 else 'ZERO')
    return pct, None

def bucket(p):
    if p is None: return 'R_UNKNOWN'
    if p <= -5: return 'L5_PLUS'
    if p <= -4: return 'L4_5'
    if p <= -3: return 'L3_4'
    if p <= -2: return 'L2_3'
    if p <= -1: return 'L1_2'
    if p < 0: return 'L0_1'
    if p == 0: return 'ZERO'
    if p < 1: return 'P0_1'
    if p < 2: return 'P1_2'
    if p < 3: return 'P2_3'
    if p < 4: return 'P3_4'
    if p < 5: return 'P4_5'
    return 'P5_PLUS'

def groups(rows):
    out = {b: [r for r in rows if r['bucket'] == b] for b in BANDS}
    out['ALL_MINUS'] = [r for r in rows if r['R'] is not None and r['R'] < 0]
    out['ALL_PLUS'] = [r for r in rows if r['R'] is not None and r['R'] > 0]
    out['R_KNOWN'] = [r for r in rows if r['R'] is not None]
    out['TOTAL'] = list(rows)
    return out

def cumulative(rows):
    out = {'ALL_MINUS': [r for r in rows if r['R'] is not None and r['R'] < 0]}
    out.update({f'R_LE_NEG{k}': [r for r in rows if r['R'] is not None and r['R'] <= -k] for k in range(1,6)})
    out['ALL_PLUS'] = [r for r in rows if r['R'] is not None and r['R'] > 0]
    out.update({f'R_GE_POS{k}': [r for r in rows if r['R'] is not None and r['R'] >= k] for k in range(1,6)})
    return out

def masses(rows):
    rr = [r['R'] for r in rows if r['R'] is not None]
    neg = sum((-v for v in rr if v < 0), Fraction(0))
    pos = sum((v for v in rr if v > 0), Fraction(0))
    return neg, pos, pos - neg

def decision_stats(rows, point):
    c = Counter(r['decisions'].get(point, 'UNKNOWN') for r in rows)
    n = len(rows)
    return {'N': n, 'KEEP': c['KEEP'], 'DROP': c['DROP'], 'decision_UNKNOWN': c['UNKNOWN'],
            'KEEP_rate_pct': rate(c['KEEP'],n), 'DROP_rate_pct': rate(c['DROP'],n),
            'decision_coverage_pct': rate(c['KEEP']+c['DROP'],n)}

def main():
    a = argparse.ArgumentParser()
    a.add_argument('--inputs', required=True)
    a.add_argument('--public', required=True)
    a.add_argument('--private', required=True)
    a.add_argument('--spec', required=True)
    args = a.parse_args()
    source, pub, prv = Path(args.inputs), Path(args.public), Path(args.private)
    pub.mkdir(parents=True, exist_ok=True); prv.mkdir(parents=True, exist_ok=True)
    spec = read(args.spec)
    assert spec['points'] == POINTS
    splits = read(source/'SPLITS_S1_S2.json')
    memberships = {s['block']: list(s['DEV_COMPARE_Entry_IDs']) for s in splits}
    assert all(len(v)==len(set(v)) for v in memberships.values())
    s1, s2 = set(memberships['S1']), set(memberships['S2'])
    # These saved canonical cohorts have no overlap; do not invent an attribution rule.
    assert not s1 & s2, 'UNRESOLVED_CANONICAL_SPLIT_ATTRIBUTION'
    ids = s1 | s2
    raw = read(source/'CANONICAL_RETURN_ROWS_322.json')
    rawmap = {r['entry_id']: r for r in raw}
    original = read(source/'RNEG_TARGETED_OUTCOMES_322.json')
    origmap = {r['entry_id']:r for r in original}
    identity = read(source/'SAVED_FROZEN_IDENTITY_322.json')
    imap = {r['entry_id']:r for r in identity}
    assert len(rawmap)==len(raw)==len(ids) and set(rawmap)==ids
    assert len(origmap)==len(original)==len(ids) and set(origmap)==ids
    assert len(imap)==len(identity)==len(ids) and set(imap)==ids
    exposure = read(source/'EXPOSURE_LEDGER.json')
    old_scope = exposure['new_exposure_events'][0]
    assert set(old_scope['Entry_IDs']) == ids
    assert exposure['all_sessions_status'] == 'ADAPTIVE_DEVELOPMENT'
    saved = gzrows(source/'C11/DEV_SCORES_DECISIONS.jsonl.gz')
    dmap = {r['entry_id']:r for r in saved}
    assert len(saved)==len(dmap)==len(ids) and set(dmap)==ids
    decision_seals = {}
    for block in ['S1','S2']:
        p = source/f'C11/{block}/DEV_COMPARE_SCORES_DECISIONS.jsonl.gz'
        rr = gzrows(p)
        seal = read(source/f'C11/{block}/PREDICTION_SEAL.json')
        b = p.read_bytes(); pin = seal['scores']['DEV_COMPARE']
        assert len(b)==pin['bytes'] and hashlib.sha256(b).hexdigest()==pin['sha256']
        assert len(rr)==pin['row_N'] and set(r['entry_id'] for r in rr)==set(memberships[block])
        for r in rr:
            assert r == dmap[r['entry_id']] and r['block']==block
        decision_seals[block] = pin
    joined=[]; private_rows=[]
    for i in sorted(ids):
        r, d, ident, old = rawmap[i], dmap[i], imap[i], origmap[i]
        block = 'S1' if i in s1 else 'S2'
        assert r['session']==d['session']==ident['session']==old['session']
        assert d['block']==block
        value, reason=primary_R(r)
        assert old['known']==r['return_available']
        if value is not None:
            assert Fraction(Decimal(str(old['r_original'])))*100==value
            assert r['buy_debit']==old['buy_debit'] and r['sell_credit']==old['sell_credit']
        decisions={}
        dreasons={}
        for p,k in POINTS.items():
            token=d.get('decisions',{}).get(k)
            decisions[p] = token if token in ('KEEP','DROP') else 'UNKNOWN'
            dreasons[p] = None if token in ('KEEP','DROP') else 'SAVED_DECISION_UNAVAILABLE' if token is None else 'INVALID_SAVED_DECISION'
        row={'entry_id':i,'session':r['session'],'symbol':ident['symbol'],'block':block,
             'R':value,'R_reason':reason,'bucket':bucket(value),'decisions':decisions}
        joined.append(row)
        private_rows.append({'entry_id':i,'session':r['session'],'symbol':ident['symbol'],'canonical_block':block,
            'partition':'DEV_COMPARE','exposure':'ADAPTIVE_DEVELOPMENT',
            'R_native_fraction_decimal':r.get('R_native_fraction_decimal'),'R_original_unit':'fraction',
            'R_unit':r.get('R_unit'),'R_pct_numerator':r.get('R_pct_numerator'),'R_pct_denominator':r.get('R_pct_denominator'),
            'R_pct_exact':exact(value),'R_reason':reason,'bucket':bucket(value),
            'return_available':r['return_available'],'teacher_source':r['source'],'source_hash':r['source_hash'],
            'raw_source_row_sha256':r.get('raw_source_row_sha256'),'buy_debit':r.get('buy_debit'),
            'sell_credit':r.get('sell_credit'),'quantity_basis':r.get('quantity_basis'),'exit_kind':r.get('exit_kind'),
            'decisions':decisions,'decision_reasons':dreasons})
    cnt=Counter(r['bucket'] for r in joined)
    # Reconciliation values are checks only. Never change input rows to match them.
    assert len(joined)==322 and sum(cnt[b] for b in BANDS[:6])==172
    assert sum(cnt[b] for b in BANDS[7:13])==144 and cnt['ZERO']==0 and cnt['R_UNKNOWN']==6
    ranges = {b[0]:b[1] for b in spec['boundaries']}
    ranges.update(ALL_MINUS='R < 0',ALL_PLUS='R > 0',R_KNOWN='正式R既知',TOTAL='DEV_COMPARE 全件')
    ranges.update({f'R_LE_NEG{k}':f'R <= -{k}%' for k in range(1,6)})
    ranges.update({f'R_GE_POS{k}':f'R >= +{k}%' for k in range(1,6)})
    census=[]; band=[]; cum=[]; comp=[]; mass=[]; accounting=[]; baseline=[]
    cohort_summary={}; point_status={}
    for cohort in ['S1','S2','UNION']:
        rr=[r for r in joined if cohort=='UNION' or r['block']==cohort]
        known_n=sum(r['R'] is not None for r in rr)
        gs,cs=groups(rr),cumulative(rr)
        cohort_summary[cohort]={'N':len(rr),'R_known_N':known_n,'R_unknown_N':len(rr)-known_n,
            'ALL_MINUS_N':len(gs['ALL_MINUS']),'ZERO_N':len(gs['ZERO']),'ALL_PLUS_N':len(gs['ALL_PLUS']),
            'sessions':sorted({r['session'] for r in rr}),'distinct_sessions':len({r['session'] for r in rr}),
            'distinct_symbols':len({r['symbol'] for r in rr}),
            'period_start':min(r['session'] for r in rr),'period_end':max(r['session'] for r in rr),
            'unknown_reasons':dict(Counter(r['R_reason'] for r in rr if r['R'] is None))}
        for group, rows in gs.items():
            vals=sorted(r['R'] for r in rows if r['R'] is not None)
            neg,pos,net=masses(rows)
            median=None if not vals else vals[len(vals)//2] if len(vals)%2 else (vals[len(vals)//2-1]+vals[len(vals)//2])/2
            census.append({'cohort':cohort,'bucket':group,'range':ranges[group],'N':len(rows),
                'R_known_N':len(vals),'R_unknown_N':len(rows)-len(vals),
                'share_R_known_pct':rate(len(vals),known_n) if group!='R_UNKNOWN' else 'N/A',
                'share_all_entries_pct':rate(len(rows),len(rr)),
                'distinct_sessions':len({r['session'] for r in rows}),'distinct_symbols':len({r['symbol'] for r in rows}),
                'R_median_pct':exact(median),'R_sum_pp':'N/A' if rows and not vals else exact(net),
                'negative_mass_abs_pp':exact(neg),'positive_mass_pp':exact(pos)})
            n=len(rows)
            baseline.append({'cohort':cohort,'comparison':'ALL_KEEP_DEFINITIONAL_ONLY','point':'ALL_KEEP','bucket':group,
                 'N':n,'KEEP':n,'DROP':0,'decision_UNKNOWN':0,'KEEP_rate_pct':rate(n,n),
                 'DROP_rate_pct':rate(0,n),'decision_coverage_pct':rate(n,n),'model_performance':False})
        for point in POINTS:
            available=sum(r['decisions'][point] in ('KEEP','DROP') for r in rr)
            status='AVAILABLE_COMPLETE' if available==len(rr) else 'SAVED_DECISION_UNAVAILABLE' if not available else 'PARTIAL_SAVED_DECISIONS'
            point_status[f'{cohort}/{point}']=status
            base={'cohort':cohort,'model':'LEGACY_C11','point':point,'diagnostic_labels':LABELS,'saved_decision_status':status}
            for group,rows in gs.items():
                band.append({**base,'bucket':group,'range':ranges[group],**decision_stats(rows,point)})
            for group,rows in cs.items():
                cum.append({**base,'group':group,'range':ranges[group],**decision_stats(rows,point)})
            total_drop=sum(r['decisions'][point]=='DROP' for r in rr)
            composition_groups={**{b:gs[b] for b in BANDS},'ALL_MINUS':gs['ALL_MINUS'],
                'R_LE_NEG5':cs['R_LE_NEG5'],'R_LE_NEG3':cs['R_LE_NEG3'],'ALL_PLUS':gs['ALL_PLUS'],
                'R_GE_POS2':cs['R_GE_POS2'],'R_GE_POS3':cs['R_GE_POS3'],'R_GE_POS5':cs['R_GE_POS5'],'TOTAL':rr}
            known_drop=sum(r['R'] is not None and r['decisions'][point]=='DROP' for r in rr)
            for group,rows in composition_groups.items():
                n=sum(r['decisions'][point]=='DROP' for r in rows)
                known=sum(r['R'] is not None and r['decisions'][point]=='DROP' for r in rows)
                comp.append({**base,'bucket':group,'row_type':'exclusive_bucket' if group in BANDS else 'overlapping_summary',
                    'DROP_N':n,'all_DROP_N':total_drop,'share_of_all_DROP_pct':rate(n,total_drop),
                    'known_R_DROP_N':known,'all_known_R_DROP_N':known_drop,
                    'aux_share_of_known_R_DROP_pct':'N/A' if group=='R_UNKNOWN' else rate(known,known_drop)})
            for group,rows in {**gs,**cs}.items():
                gneg,gpos,gnet=masses(rows)
                for part in ['ALL','KEEP','DROP','DECISION_UNKNOWN']:
                    selected=rows if part=='ALL' else [r for r in rows if r['decisions'][point]==('UNKNOWN' if part=='DECISION_UNKNOWN' else part)]
                    neg,pos,net=masses(selected); known=sum(r['R'] is not None for r in selected)
                    mass.append({**base,'group':group,'range':ranges[group],'decision_partition':part,
                        'group_N':len(rows),'partition_N':len(selected),'R_known_N':known,'R_unknown_N':len(selected)-known,
                        'negative_mass_abs_pp':exact(neg),'positive_mass_pp':exact(pos),'net_R_pp':exact(net),
                        'negative_mass_share_of_group_pct':massrate(neg,gneg),
                        'positive_mass_share_of_group_pct':massrate(pos,gpos),
                        'mass_unit':'pp-sum','mass_scope':'SAVED_KNOWN_R_ONLY','capitalImprovement':'NOT_EVALUATED'})
            same=[r for r in rr if r['R'] is not None and r['decisions'][point] in ('KEEP','DROP')]
            keep=[r for r in same if r['decisions'][point]=='KEEP'];drop=[r for r in same if r['decisions'][point]=='DROP']
            allnet=masses(same)[2];keepnet=masses(keep)[2];dropnet=masses(drop)[2]
            residual=keepnet-allnet+dropnet
            assert residual==0
            accounting.append({**base,'R_and_decision_known_N':len(same),
                'excluded_R_unknown_N':sum(r['R'] is None for r in rr),
                'excluded_R_known_decision_unknown_N':sum(r['R'] is not None and r['decisions'][point]=='UNKNOWN' for r in rr),
                'R_sum_KEEP_pp':exact(keepnet),'R_sum_ALL_KNOWN_DECISION_pp':exact(allnet),
                'negative_R_sum_DROP_pp':exact(-dropnet),'KEEP_minus_ALL_pp':exact(keepnet-allnet),
                'identity_residual_pp':exact(residual),'identity_PASS':True})
    csvwrite(pub/'ENTRY_EXIT_R_DISTRIBUTION.csv',census)
    csvwrite(pub/'LEGACY_R_BAND_KEEP_DROP.csv',band)
    csvwrite(pub/'CUMULATIVE_LOSER_WINNER_KEEP_DROP.csv',cum)
    csvwrite(pub/'DROP_COMPOSITION.csv',comp)
    csvwrite(pub/'RETURN_MASS_DECOMPOSITION.csv',mass)
    csvwrite(pub/'ACCOUNTING_IDENTITY_CHECK.csv',accounting)
    csvwrite(pub/'ALL_KEEP_REFERENCE.csv',baseline)
    dump(pub/'CENSUS_SUMMARY.json',{'cohorts':cohort_summary,'split_overlap_N':0,'canonical_attribution':'S1/S2 saved DEV membership; disjoint',
        'point_status':point_status,'legacy_labels':LABELS,'newFirstLayerSelected':None,'productionReady':False,'capitalImprovement':'NOT_EVALUATED'})
    dump(pub/'NEW_FIRST_LAYER_STATUS.json',{'status':'NEW_FIRST_LAYER_NOT_RUN','designed':False,'implemented':False,'fit':0,
        'KEEP':None,'DROP':None,'decision_coverage':None,'newFirstLayerSelected':None,'productionReady':False,'capitalImprovement':'NOT_EVALUATED'})
    dump(pub/'MISSING_EVIDENCE.json',{'missing_required_sources':[], 'saved_decision_unavailable_points':[],
        'R_unknown_N':6,'R_unknown_reason':'FORMAL_R_UNAVAILABLE_SOURCE_REASON_UNSPECIFIED',
        'unknown_rows_retained':True,'source_finer_unknown_reason_not_saved':True,'R_unknown_subbucket_not_imputed':True})
    with (prv/'ENTRY_R_DECISION_JOIN.jsonl').open('w',encoding='utf-8') as f:
        for r in private_rows: f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n')
    files=[x.name for x in pub.iterdir() if x.suffix in ('.csv','.json')]
    print(json.dumps({'status':'PRIMARY_CENSUS_COMPLETE','cohorts':cohort_summary,
        'saved_points':list(POINTS),'output_files':sorted(files),'fits':0,'inference':0,'threshold_reapplication':0},ensure_ascii=False))

if __name__=='__main__':
    main()
