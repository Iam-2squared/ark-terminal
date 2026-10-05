"""P1: same-hash original certificates and pure native wrapper saved-case verification."""
from context import *
from policy import native_wrapper, project_packet, HEADS
from collections import Counter
import struct

def bits(x):return struct.pack('>d',x)

def main():
    get=json.loads((OUT/'receipts/P0_ACTUAL_GET.json').read_text())
    assert get['verified_commit']==subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    assert sha(OUT/'DIRECTIVE.txt')==get['directive_sha256_expected']
    certificate=read('score_certificate');assert certificate['status']=='PASS'
    assert sha(INPUT/ROLES['packet'])=='6f47f616cab22e5fe749638b69fee7b7152724c8c901a44e3c50aa0e66c514f6'
    packet=read('packet');canonical_scores={r['entry_id']:r for r in read('canonical_scores')}
    refs=read('reference32');refmap={(r['block'],r['head']):r for r in refs}
    reused_refs={(r['block'],r['head']):r for r in read('reference_certificate')['ordered_reference_checks']}
    checks=Counter();mismatch=[]
    split=read('split');block_sessions={b['block']:b['test'] for b in split['blocks']}
    native_git=[]
    for name in ('allocation.py','execution.py','slot_policy.py','staircase.py','replay.py'):
        p=NATIVE_ROOT/name;b=p.read_bytes()
        actual_blob=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        git_blob=subprocess.check_output(['git','rev-parse',PARENT+':research/capital-v5-max3-slot-intelligence-20261004-v1/'+name],cwd=REPO,text=True).strip()
        assert actual_blob==git_blob,'FROZEN_NATIVE_CODE_CHANGED'
        native_git.append({'file':name,'sha256':sha(p),'git_blob':git_blob,'parent':PARENT});checks['native_source_exact']+=1
    for ref in refs:
        h,b=ref['head'],ref['block'];rr=reused_refs[b,h]
        assert ref['reference_N']==len(ref['ordered_reference'])==len(ref['scores'])==rr['N']
        assert len(ref['train_identity_order'])==len(set(ref['train_identity_order']))==ref['reference_N']
        assert ref['train_identity_sha256']==rr['ordered_training_identity_sha256']
        for a,score,key in zip(ref['ordered_reference'],ref['scores'],ref['train_identity_order']):
            assert a['entry_id']==key and a['session']<min(block_sessions[b]) and bits(a['score'])==bits(score)
            checks['reference_identity_bits_past']+=1
        checks['head_specific_reference_sets']+=1
    for p in packet:
        old=canonical_scores[p['entry_id']]
        assert p['session'] in block_sessions[p['native_block']] and p['native_block']==old['block']
        checks['current_identity_split']+=1
        for h in HEADS:
            q=p['heads'][h];src=old[h];ref=refmap[p['native_block'],h];rr=reused_refs[p['native_block'],h]
            assert bits(q['raw_score'])==bits(src['score'])
            assert q['numerator']==src['rank_numerator'] and q['denominator']==src['rank_denominator']==ref['reference_N']+1
            assert q['model_hash']==src['model_sha256']==ref['model_sha256']
            assert q['training_reference_hash']==src['reference_sha256']==rr['ordered_score_reference_sha256']
            assert q['prediction_origin']['train_through']<p['session']
            assert q['score_asof']==p['frozen_entry_time'] and q['feature_max_source_minute']<p['entry_minute']
            checks['current_score_binary64_reference_asof']+=1
        assert set(project_packet(p)['scores'])==set(HEADS)
    tables=read('arrival');proposals=read('proposals')
    for p in proposals:
        assert p['existing_open_N']==len(p['snapshot']['positions'])
        actual=native_wrapper(p['candidates'],p['snapshot'],p['session'],p['minute'],tables[str(p['candidates'][0]['block'])])
        if actual['picked_ids']!=p['picked_ids'] or actual['assigned']!=p['assigned']:
            mismatch.append({'session':p['session'],'minute':p['minute'],'kind':'PICKS_OR_ALLOCATION','actual':actual,'expected':p})
        for a,s in zip(actual['gate_decisions'],p['gate_decisions']):
            for key,val in a.items():
                if s.get(key)!=val:mismatch.append({'entry_id':a['entry_id'],'field':key,'actual':val,'saved':s.get(key)})
                checks['native_wrapper_saved_field_exact']+=1
        checks['native_saved_batches']+=1
    prior=json.loads((SCRATCH/'work/r1_remote/V5_OFF_EQUIVALENCE.json').read_text())
    off_complete=json.loads((SCRATCH/'work/r1_remote/receipts/OFF_PRIMARY_COMPLETE.json').read_text())
    assert prior['status']=='PASS' and prior['mismatch_N']==0
    assert sha(INPUT/ROLES['proposals'])==off_complete['artifacts']['native_proposals']['compressed_sha256']
    for typ,role in [('DECISIONS','native_decisions'),('TRADES','native_trades'),('INTENTS','native_intents'),('CURVE','native_curve')]:
        assert sha(INPUT/ROLES[role])==prior['artifacts'][typ]['original_sha256']
        checks['OFF_receipt_source_hash_reuse']+=1
    save('INPUT_BINDING_COLUMN_RECEIPT.json',{'schema':'V5_R_INPUT_COLUMN_BINDING_CORRECTION_V1','exact_jst':now(),
        'original_binding_sha256':sha(OUT/'INPUT_BINDING.json'),
        'reason':'Reference metadata column names corrected to actual saved schema; no input bytes/population/policy change',
        'reference32_actual_columns':['block','head','model_sha256','ordered_reference','reference_N','scores','train_identity_order','train_identity_sha256'],
        'score_reference_hash_source':'bridge_work/evidence/REFERENCE_HASH_AND_CERTIFICATE_REUSE.json:ordered_reference_checks[].ordered_score_reference_sha256',
        'previous_metadata_only_reference_sha256_column_absent':True,'fixed_scope':'PATH_SCHEMA_METADATA_ONLY',
        'source_or_policy_changes':0})
    result={'schema':'V5_R_P1_PACKET_OFF_REUSE_V1','exact_jst':now(),'status':'PASS' if not mismatch else 'IMPLEMENTATION_BLOCKED',
        'packet_N':len(packet),'current_score_copies_checked':checks['current_score_binary64_reference_asof'],
        'reference_head_block_N':len(refs),'native_batch_N':len(proposals),'checks':dict(checks),
        'mismatch_N':len(mismatch),'mismatches':mismatch,'native_git_source_identity':native_git,
        'original_accuracy_certificate_hashes':{role:sha(INPUT/ROLES[role]) for role in ('original_skill_certificate','score_certificate','materialization_certificate','reference_certificate')},
        'original_accuracy_recalculation':0,'model_inference':0,'new_OFF_market_replay':0,
        'prior_OFF_body_hash':sha(SCRATCH/'work/r1_remote/V5_OFF_EQUIVALENCE.json'),
        'snapshot_execution_contract':'BUY is immediate at Frozen Entry; pending future SELL remains held until confirmed; no external outstanding BUY orders',
        'historical_actual_arrival':'UNKNOWN inherited closed-bar assumed availability; no external feed-timing proof'}
    save('P1_PACKET_AND_OFF_AUDIT.json',result)
    checkpoint('P1',result['status'],{'packet_N':len(packet),'saved_native_batches':len(proposals),'mismatch_N':len(mismatch)},
        'Build outcome-blind one-proposal-per-session S and hash it before any new past outcome join')
    assert not mismatch,'P1_NATIVE_WRAPPER_MISMATCH_STOP'
    print(json.dumps({k:result[k] for k in ('status','packet_N','reference_head_block_N','native_batch_N','mismatch_N')}))

if __name__=='__main__':main()
