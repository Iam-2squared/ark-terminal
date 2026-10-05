"""P2a: fix S before labels, probe native singleton once per selected actual snapshot."""
from context import *
from policy import project_packet, proposal, singleton, RESERVE
from collections import Counter

def summary(rows):
    return {'N':len(rows),'sessions':len({r['session'] for r in rows}),
        'blocks':len({r['block'] for r in rows}),'by_block':dict(Counter(str(r['block']) for r in rows))}

def main():
    assert json.loads((OUT/'P1_PACKET_AND_OFF_AUDIT.json').read_text())['status']=='PASS'
    packet={r['entry_id']:project_packet(r) for r in read('packet')}
    saved=read('proposals');probes=[];S=[];collection_done=set();water=Counter();struct=[]
    for index,p in enumerate(saved):
        reserve=[d for d in p['gate_decisions'] if d.get('slot_gate_reason') in RESERVE]
        for d in reserve:struct.append({'entry_id':d['entry_id'],'session':p['session'],'block':packet[d['entry_id']]['block']})
        if not reserve:continue
        water['structural_reserve_rows']+=len(reserve);water['structural_reserve_batches']+=1
        if p['picked_ids']:
            water['native_picked_nonempty_rows']+=len(reserve);continue
        water['native_picked_empty_rows']+=len(reserve);water['native_picked_empty_batches']+=1
        result=proposal(p['candidates'],p,p['snapshot'],packet,p['session'],p['minute'])
        key=result.get('candidate')
        if not key:
            probes.append({'snapshot_index':index,'snapshot_hash':digest(p),'session':p['session'],
                'minute':p['minute'],'block':p['candidates'][0]['block'],'result':result,'quantity_probe_executed':False})
            water[result['reason']]+=1;continue
        row=next(r for r in p['candidates'] if r['entry_id']==key)
        a=result.get('allocation')
        score_pass=a is not None
        if a is None:
            # Diagnostic quantity of the fixed first candidate; does not change a rejected action.
            a=singleton(row,p['snapshot'])
        probe={'snapshot_index':index,'snapshot_hash':digest(p),'session':p['session'],'minute':p['minute'],
            'block':row['block'],'candidate':key,'pool_ids':result['pool_ids'],
            'native_reason':result['native_reason'],'reason':result['reason'],'score_pass':score_pass,
            'allocation':a,'scores':packet[key]['scores'],'snapshot':p['snapshot'],'row':row,
            'quantity_probe_executed':True,'singleton_call_N':1,'state_mutation':False,
            'collection_already_ended':p['session'] in collection_done}
        probes.append(probe);water['raw_pP_first_selected']+=1
        water['diagnostic_singleton_probe_N']+=1
        if a['quantity']>=100:water['all_selected_snapshot_fundable']+=1
        else:water[a['fundability_reason']]+=1
        if score_pass:
            water['score_pass']+=1
            if a['quantity']>=100:water['score_pass_snapshot_fundable']+=1
        else:water[result['reason']]+=1
        if score_pass and a['quantity']>=100 and p['session'] not in collection_done:
            S.append({'entry_id':key,'session':p['session'],'block':row['block'],'minute':p['minute'],
                'snapshot_index':index,'snapshot_hash':digest(p),'native_reason':result['native_reason'],
                'quantity':a['quantity'],'debit':a['debit'],'allocation':a,'scores':packet[key]['scores']})
            collection_done.add(p['session'])
    assert len(S)==len({x['session'] for x in S})
    sp=gzsave('PAST_PROPOSALS_OUTCOME_BLIND.jsonl.gz',S)
    pp=gzsave('SHADOW_NATIVE_SNAPSHOT_PROBES.jsonl.gz',probes)
    manifest={'schema':'V5_R_OUTCOME_BLIND_PAST_PROPOSAL_FREEZE_V1','exact_jst':now(),
      'S_hash_fixed_before_new_outcome_join':True,'S_canonical_identity_hash':digest(S),'S_artifact_sha256':sha(sp),
      'S_artifact':'private/PAST_PROPOSALS_OUTCOME_BLIND.jsonl.gz','probe_artifact':'private/SHADOW_NATIVE_SNAPSHOT_PROBES.jsonl.gz',
      'probe_sha256':sha(pp),'S':summary(S),'structural_reserve':summary(struct),
      'probes':summary(probes),'waterfall':dict(water),'S_ids':[s['entry_id'] for s in S],
      'collection_rule':'first fixed-rule singleton quantity>=100 per session, then collection ends',
      'historical_policy_replay':False,'actual_recovered_PnL':False,'new_path_created':False,
      'source_feature_or_future_availability_access':False,'outcome_access_during_collection':False,
      'native_picked_definition':'pre-allocation native ADMIT IDs; nonempty all-qty0 remains nonempty',
      'each_real_selected_snapshot_native_singleton_calls_max':1,'code_hashes':{p.name:sha(p) for p in CODE.glob('*.py')},
      'source_hashes':{r:sha(INPUT/ROLES[r]) for r in ('packet','proposals','arrival','reference32')}}
    save('PAST_PROPOSAL_MANIFEST.json',manifest)
    checkpoint('P2A','PAST_PROPOSAL_IDENTITIES_FIXED_BEFORE_LABELS',{'S':summary(S),'waterfall':dict(water)},
        'Commit S manifest actual GET before joining only matured prior OOF labels; no market replay')
    print(json.dumps({'S':summary(S),'waterfall':dict(water)}))

if __name__=='__main__':main()
