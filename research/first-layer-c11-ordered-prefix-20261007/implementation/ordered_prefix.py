"""One precommitted pure maximal sign-run representation; no teacher or IO."""
import math
from causal_prefix import identity_check, bar_check, active

METRICS = ['present','direction','net_log_return','observed_duration_minutes',
           'active_minutes','gross_log_movement','high_low_log_excursion',
           'slope_per_active_minute','log1p_volume','log1p_value',
           'log1p_volume_per_active_minute','log1p_value_per_active_minute',
           'end_vs_two_back_high','end_vs_two_back_low']
TRANSITIONS = ['same_chain','slope_change','volume_activity_change','value_activity_change']

def linked(a,b):
    return b-a==1 and (540<=a<=690 and 540<=b<=690 or 750<=a<=925 and 750<=b<=925)

def segment(case):
    if set(case)!={'identity','prefix'}:raise ValueError('UNAUTHORIZED_ORDERED_PREFIX_CAPABILITY')
    ident=case['identity'];identity_check(ident);bars=case['prefix'];cut=ident['cutoff_minute']
    for b in bars:
        if b[0]+1>cut:raise ValueError('POST_BUY_INTENT_CAPABILITY')
        bar_check(b)
    if any(a[0]>=b[0] for a,b in zip(bars,bars[1:])):raise ValueError('UNORDERED_OR_DUPLICATE_PREFIX')
    legs=[];chain=-1;previous=None
    for b in bars:
        connected=previous is not None and linked(previous[0],b[0])
        if not connected:chain+=1
        anchor=previous[4] if connected else b[1]
        direction=1 if b[4]>anchor else -1 if b[4]<anchor else 0
        edge=math.log(b[4]/anchor)
        if not legs or not connected or legs[-1]['direction']!=direction:
            legs.append({'chain':chain,'direction':direction,'start':b[0],'end':b[0]+1,
                         'seed':anchor,'last':b[4],'high':max(anchor,b[2]),'low':min(anchor,b[3]),
                         'gross':abs(edge),'volume':b[5],'value':b[6],'bar_minutes':[b[0]]})
        else:
            g=legs[-1];g['end']=b[0]+1;g['last']=b[4];g['high']=max(g['high'],b[2]);g['low']=min(g['low'],b[3])
            g['gross']+=abs(edge);g['volume']+=b[5];g['value']+=b[6];g['bar_minutes'].append(b[0])
        previous=b
    for k,g in enumerate(legs):
        g['net']=math.log(g['last']/g['seed']);g['active']=float(active(g['start'],g['end']))
        g['slope']=g['net']/g['active'] if g['active'] else None
        g['volume_rate']=math.log1p(g['volume']/g['active']) if g['active'] else None
        g['value_rate']=math.log1p(g['value']/g['active']) if g['active'] else None
        older=legs[k-2] if k>=2 and legs[k-2]['chain']==g['chain'] else None
        g['vs_high']=math.log(g['last']/older['high']) if older else None
        g['vs_low']=math.log(g['last']/older['low']) if older else None
    return legs

def build_ordered(case):
    legs=segment(case);kept=[None]*max(6-len(legs),0)+legs[-6:]
    out={'C11.phase_count':float(len(legs)),'C11.omitted_phase_count':float(max(len(legs)-6,0)),
         'C11.chain_count':float(legs[-1]['chain']+1) if legs else 0.}
    for k,g in enumerate(kept):
        values={n:None for n in METRICS};values['present']=float(g is not None)
        if g:
            values.update(direction=float(g['direction']),net_log_return=g['net'],
                          observed_duration_minutes=float(g['end']-g['start']),active_minutes=g['active'],
                          gross_log_movement=g['gross'],high_low_log_excursion=math.log(g['high']/g['low']),
                          slope_per_active_minute=g['slope'],log1p_volume=math.log1p(g['volume']),
                          log1p_value=math.log1p(g['value']),log1p_volume_per_active_minute=g['volume_rate'],
                          log1p_value_per_active_minute=g['value_rate'],end_vs_two_back_high=g['vs_high'],
                          end_vs_two_back_low=g['vs_low'])
        out.update({f'C11.phase{k}.'+n:v for n,v in values.items()})
    for k in range(1,6):
        a,b=kept[k-1],kept[k];v={n:None for n in TRANSITIONS}
        if a and b:
            same=a['chain']==b['chain'];v['same_chain']=float(same)
            if same:
                for n,src in [('slope_change','slope'),('volume_activity_change','volume_rate'),('value_activity_change','value_rate')]:
                    v[n]=b[src]-a[src] if a[src] is not None and b[src] is not None else None
        out.update({f'C11.transition{k-1}_{k}.'+n:x for n,x in v.items()})
    if len(out)!=107 or not all(x is None or math.isfinite(x) for x in out.values()):raise ValueError('REGISTRY_OR_FINITE_OUTPUT')
    return out
