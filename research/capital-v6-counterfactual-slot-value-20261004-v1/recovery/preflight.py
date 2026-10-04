"""Read-only identity and resume gate. Never invokes replay, teacher or fit."""
import ast, gzip, json, math
from pathlib import Path
from control import ROOT, WORK, OUT, now, save, sha

def main():
    code = ROOT / 'research/capital-v6-counterfactual-slot-value-20261004-v1'
    frozen = WORK / 'source_main/capital_staircase_v4_private'
    state = json.loads((WORK / 'v6_recovery_publication_state.json').read_text())
    checks = {}
    for path, digest in state['known_sha256'].items():
        if path.endswith('WORK_STATUS_LOG.jsonl'):
            continue
        if path.startswith(('docs/evidence/capital-v6-', 'research/capital-v6-')):
            checks['preserve:' + path] = sha(ROOT / path) == digest
    expected = {
        'TEACHER_PRECOMMIT.json': '9adf9bb86e0123a1450750ad5b6d874e73871a0412364b08f33fea229330f1f1',
        'SLOT_MODEL_PRECOMMIT.json': '85ff3a3cbe6840171831fa1dd7d8e372da9a7acfcfba48328c23de6cfdfcf286',
        'SOURCE_HASHES.json': '076e5094b7d9cbc2234b21e2a33aed041f8df26b3dbaeee19cd95365a0a0aeed',
    }
    checks.update({n: sha(OUT/n) == h for n,h in expected.items()})
    freeze = json.loads((OUT/'SCORE_ACTION_FREEZE.json').read_text())
    amendment = json.loads((OUT/'TEACHER_PRECOMMIT_U5_PRIORITY_AMENDMENT.json').read_text())
    checks['U5_precommitted_before_teacher_fit_and_main'] = (
        amendment['main_replay_at_amendment'] == amendment['slot_fits_at_amendment'] == amendment['teacher_generated_at_amendment'] == 0
        and amendment['effective_action'] == 'if current_U5 and ACCEPT_U5>=RESERVE_U5 then ACCEPT; else compare full lex tuple')
    checks['threshold'] = freeze['threshold'] == .5
    checks['runtime_code_frozen'] = all(sha(code/n) == h for n,h in freeze['code'].items())
    checks['arrival_frozen'] = sha(ROOT/'docs/evidence/capital-v5-max3-slot-intelligence-20261004-v1/ARRIVAL_TABLE.json') == freeze['arrival_table_sha256']
    checks['score_frozen'] = sha(frozen/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz') == freeze['rank_score_stream_sha256']
    models = {}
    for b, digest in freeze['models'].items():
        p = OUT/'models'/f'SLOT_MODEL_BLOCK_{int(b):02d}.json'
        checks[f'model_{b}'] = sha(p) == digest == sha(WORK/'capital_v6_slot_private'/p.name)
        models[b] = json.loads(p.read_text())
    support = json.loads((OUT/'TEACHER_CENSUS_SUPPORT_GATE.json').read_text())
    pre = json.loads((OUT/'SLOT_MODEL_PRECOMMIT.json').read_text())
    checks['all8_support_pass'] = support['all_8_support_pass'] and len(support['blocks']) == 8
    checks['model_preprocessing_family_action'] = all(
        m['threshold']==.5 and m['family']=='LogisticRegression' and m['winner_fit']==m['within_block_refit']==0
        and m['effective_teacher_precommit_sha256']==sha(OUT/'TEACHER_PRECOMMIT_U5_PRIORITY_AMENDMENT.json')
        and m['preprocessing']['numeric_fields']==pre['numeric_features']
        and m['preprocessing']['categorical_fields']==pre['categorical_features']
        and all(math.isfinite(v) for v in m['coef'])
        and m['teacher_sha256']==support['blocks'][int(b)-1]['teacher_sha256']
        for b,m in models.items())
    score = [json.loads(line) for line in gzip.open(frozen/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz','rt')]
    identities = json.loads((frozen/'MODEL_HASHES.json').read_text())
    checks['winner_models_frozen'] = all(sha(frozen/'models'/n)==h for n,h in identities.items())
    checks['winner_stream_model_identities'] = all(all(r[f'H{h}_hash']==identities[f'H{h}_BLOCK_{r["block"]:02d}.json'] for h in (2,3,5)) for r in score)
    checks['rank_mapping_1039rows_38days'] = len(score)==1039 and len({r['session'] for r in score})==38 and all(r['capital_score']==r['ML'] and r['admission']==(r['ML']>=1) and r['rank']==('S' if r['ML']>=2 else 'A' if r['ML']>=1.5 else 'B' if r['ML']>=1 else 'C') for r in score)
    checks['rolling_origin_models'] = all(r['session'] in models[str(r['block'])]['test_sessions'] and max(models[str(r['block'])]['train_sessions']) < r['session'] for r in score)
    imports = {}
    for name in ['replay.py','common.py','allocation.py','execution.py','features.py','slot_runtime.py','slot_model.py','staircase.py']:
        tree = ast.parse((code/name).read_text())
        imports[name] = [node.module or '' for node in ast.walk(tree) if isinstance(node,ast.ImportFrom)] + [alias.name for node in ast.walk(tree) if isinstance(node,ast.Import) for alias in node.names]
    checks['runtime_teacher_oracle_imports0'] = not any('teacher' in i.lower() or 'oracle' in i.lower() for values in imports.values() for i in values)
    checks['single_arm_no_fit_no_retune_no_control'] = freeze['slot_fit']==8 and freeze['winner_fit']==freeze['retune']==freeze['new_arm']==freeze['runtime_teacher_oracle_imports']==0
    checks['main_not_executed'] = not (OUT/'MAIN_REPLAY_RESULT.json').exists() and not (OUT/'checkpoints/D7_V6_MAIN_REPLAY_END.json').exists() and not (WORK/'capital_v6_slot_private/MAIN_REPLAY_STARTED.json').exists()
    checks['Safety_all_false'] = not any(amendment['safety'].values())
    failed = [k for k,v in checks.items() if not v]
    if failed:
        raise RuntimeError(('RECOVERY_HASH_MISMATCH_OR_PREFLIGHT_FAILURE', failed))
    save(OUT/'RECOVERY_D7_PREFLIGHT.json', {
        'exact_jst': now(), 'status':'PASS', 'checks':checks, 'mismatch_N':0,
        'runtime_imports':imports, 'models':freeze['models'], 'threshold':.5,
        'policy':'COUNTERFACTUAL_SLOT_VALUE_V6_MAX3',
        'Entry_EXIT_MTM_EOD_cost':'Exact D6 byte-frozen code and D1 input hashes',
        'MAX3_LONG_cash_equity_physical_only':True,
        'replacement':0,'early_sell':0,'later_topup':0,'forced_backfill':0,
        'winner_fit':0,'Slot_additional_fit':0,'control_replay':0,'retune':0,
        'same_minute':'v4 ordering, sequential pending occupancy, exact frozen allocator',
        'source_input_identity_sha256':sha(OUT/'RECOVERY_INPUT_IDENTITY.json'),
        'Safety':amendment['safety']})
    print(json.dumps({'status':'PASS','check_N':len(checks),'mismatch_N':0,'main_replay':0,'exact_jst':now()}))

if __name__ == '__main__':
    main()
