"""P0 source binding and complete fixed-design precommit, before proposal/outcome joins."""
from context import *
import shutil

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    directive=SCRATCH/'work/bridge_public/DIRECTIVE.txt'
    assert sha(directive)=='1df3aea1ebadacff7b0a329ddfb580cfcc1f24e33f50a17885b89a99e27688c3'
    assert not (OUT/'DIRECTIVE.txt').exists()
    shutil.copyfile(directive,OUT/'DIRECTIVE.txt')
    zip_path=SCRATCH/'work/downloads/Ark_Capital_V5_Frozen_Expert_Bridge_Feasibility_20261005_PRIVATE.zip'
    assert sha(zip_path)=='a31eae5a5aea92bcd96bcc093e8379f588d801faee7858b2265a1de150401686'
    manifest=INPUT/'bridge_work/evidence/PRIVATE_MANIFEST.json'
    assert sha(manifest)=='47044496512f100b2fdfda18bb47e237d49b56b6fd07c86a1c8ac8ce0d1f7ff1'
    mf=json.loads(manifest.read_text());members={x['member']:x for x in mf['payload_members']}
    for key in ROLES.values():
        x=members[key];assert (INPUT/key).stat().st_size==x['bytes'] and sha(INPUT/key)==x['sha256']
    binding={
      'schema':'V5_R_ACTUAL_INPUT_BINDING_V1','exact_jst':now(),'input_root_actual':str(INPUT),
      'source_archive':{'actual_path':str(zip_path),'bytes':zip_path.stat().st_size,'sha256':sha(zip_path),
         'manifest_actual_path':str(manifest),'manifest_sha256':sha(manifest),'payload_members_verified':298},
      'roles':{role:{'member':member,'actual_path':str(INPUT/member),'bytes':members[member]['bytes'],
          'sha256':members[member]['sha256']} for role,member in ROLES.items()},
      'native_source_root_actual':str(NATIVE_ROOT),
      'native_code':{p.name:{'actual_path':str(p),'sha256':sha(p)} for p in sorted(NATIVE_ROOT.glob('*.py'))},
      'columns':{
        'packet':{'identity':['entry_id','session','symbol','entry_minute','frozen_entry_time','native_block'],
                  'scores':'heads.{pP,MOVE_U2,MOVE_U3}.{raw_score,numerator,denominator,available,score_asof,feature_max_source_minute,prediction_origin,model_hash,training_reference_hash}'},
        'reference32':'block,head,ordered_reference[].{entry_id,session,score},reference_sha256,model_sha256',
        'native_snapshot':'session,minute,candidates[],gate_decisions[],picked_ids[],assigned[],existing_open_N,snapshot.{cash,equity,exposure,positions}',
        'quantity':'candidate.capital_score,raw_reference,rank;positions.{band,mark,quantity,symbol}',
        'past_outcome':'teachers.{entry_id,session,execution_status,capture_complete,source_minute,release_minute,potential_return,realized_net_return,buy_effective,sell_effective,source_lineage}',
        'outcome_authority':'OUTCOMES_EXACT_EVALUATION[entry_id].{potential_pct,frozen_realized_net_return_cell,frozen_execution_status}',
        'native_eod':'native_result.daily_series[].{session,status,starting_cash,ending_cash}',
        'mtm':'native_curve[].{session,minute,equity,cash,exposure,known_marks}',
        'execution':'books.{entry_id,session,market[],frozen_exit,entry_actual_source,capture_complete,limit_up_authority}'},
      'original_certificates':'READ_ONLY_HASH_BODY_REUSE; NO_AUC_OR_ORIGINAL_BOOTSTRAP_RECALCULATION',
      'OFF_receipts':{p.name:{'actual_path':str(p),'sha256':sha(p)} for p in sorted((SCRATCH/'work/r1_remote').rglob('*.json'))},
      'missing_core_inputs':[],'new_source_switch':False,'source_regeneration':False,
      'historical_actual_arrival':'UNKNOWN / inherited assumed closed-bar-end availability, no stronger provider timing claim',
      'label_maturity':'To be certified per prior OOF identity against saved completed-session teacher/source contract before qualification; unknown never imputed',
    }
    save('INPUT_BINDING.json',binding)
    delivery=json.loads((SCRATCH/'work/bridge_public/directive_delivery.json').read_text())
    design={
      'schema':'V5_R_DESIGN_PRECOMMIT_V1','exact_jst':now(),'document_id':PROFILE+'_20261005',
      'profile':PROFILE,'strategy_parent':PARENT,'branch':BRANCH,'new_evidence_path':str(OUT.relative_to(REPO)),
      'bridge_HEAD_verified':'0bb1173854217e5533d01dff13d1d9e1db98312b',
      'bridge_expected_HEAD':'fd896294400f00317486001ba763472564388c5d',
      'bridge_difference':'append-only full-directive and verified delivery; F9 closure preserved',
      'prior_terminal':'EXPERT_BRIDGE_INCONCLUSIVE / F9_CLOSURE_FIXED_STOP','candidate_branch_actual_GET':'404_NOT_FOUND',
      'original_2cards_read':True,'old_cycle_resumed':False,'duplicate_claim_detected':False,
      'directive':{'bytes':34119,'lines':515,'sha256':sha(OUT/'DIRECTIVE.txt'),
         'actual_GET_git_blob_sha':'fa81b475448fe577583d3e1b0ee150ed8165e661','authority':'GitHub full text explicitly permitted by current user'},
      'policy':delivery['policy'],
      'qualification':{'H0':'exact identity/asof/original score/reference/matured outcome/quantity',
        'H1':{'S_N_min':10,'S_sessions_min':10,'S_blocks_min':2,'F_N_min':20,'F_sessions_min':8,'S_U5_min':2,'S_U10_min':1},
        'H2':'mean S net return strictly>0','H3':'session proxy bootstrap CI95 lower strictly>0',
        'H4':'every leave-one-session-out S mean strictly>0','H5':['U5_S>=U5_F','U10_S>=U10_F','U3_S>=U3_F'],
        'H6':['Weak_S<=Weak_F','realized_nonpositive_S<=realized_nonpositive_F'],
        'past_scope':'only original prior OOF blocks with completed matured outcomes before current block start; no warmup/current-block/future',
        'S':'first singleton-quantity>=100 fixed-rule proposal per prior session; freeze identity collection hash before labels',
        'F':'all V5 actual funded trades over same original prior OOF block range; no slot/band subset',
        'bootstrap':{'seed':'571005310+b','generator':'PCG64','resamples':1999,'frame':'all preceding OOF sessions including empty',
           'unit':'one net return per session; proposal-absent zero','statistic':'arithmetic mean of resampled session proxy',
           'percentiles':[2.5,97.5],'method':'linear','valid_required':1999,'pair_generation':False},
        'second_stage_outcome_artifact':True,'no_fit_implies_no_adaptation_claim':False},
      'allocation':{'CAP':{'S':'.45','A':'.35','B':'.25'},'BASE':{'S':'.68','A':'.56','B':'.44'},
        'target_cap':'.92','increment':'.055','BUY':'1.0005','SELL':'.9995','commission':0,'lot':100,'MAX3':3,
        'capital_score':'unchanged native ML','source_is_authority':True,'source_formula_mismatch':'STOP',
        'forced_minlot':False,'same_batch_backfill':False,'natural_exit_counter_reset':False},
      'gates':delivery['acceptance'],
      'primary_economics':{'normalized_origin_jpy':1000000,'sessions':38,'window_sessions':20,'windows':19,
        'comparison':'Decimal source->Fraction, exact crossing products','loss_tolerance':0,'metric_tolerance':1e-12,
        'E0':'38 COMPLETE, unresolved0, identical19 IDs','E1':'all19 R>=V5',
        'E2':'both mean and median strictly>V5','E3':'min/max/2x noninferior and below1m windows0',
        'E4':'each paired minute-MTM MaxDD and full MaxDD<=V5'},
      'budget':{'qualification_tables_max':8,'snapshot_probe_per_selected_case_max':1,'first_divergence_primary_max':1,
        'first_divergence_independent_max':1,'primary_R_market_replay_max':1,'independent_R_reconstruction_max':1,
        'new_V5_OFF_or_other_market_replays':0,'fits_inference_calibration_source_change':0,'threshold_changes':0},
      'frozen_scope':'Full directive Sections4,16; Selector/Entry/EXIT/rank/admission/arrival/MAX3/sizing/asof unchanged',
      'runtime_firewall':'No current/future outcomes, protected IDs, source-availability exclusion lists or MRET use',
      'status_priority':'Directive Section17 order without retuning',
      'Safety':SAFETY,'counts':ZERO_COUNTS,'activeCapitalChampion':'V5','selectedCapitalCandidate':None,
      'selectedResearchCandidate':None,'championUpdated':False,'Exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE',
      'future_no_loss_guarantee':False,'fresh_OOS_claim':False,'all_future_month_noninferiority_guarantee':False,
    }
    save('DESIGN_PRECOMMIT.json',design)
    wf=json.loads((SCRATCH/'work/workflow_new_branch_parse.json').read_text())
    old=read('bridge_work/evidence/WORKFLOW_TRIGGER_CHECK.json')
    assert wf['tree']==old['tree_authority'] and len(wf['records'])==old['workflow_N']==353 and not wf['push_matches']
    save('WORKFLOW_TRIGGER_REUSE.json',{'schema':'V5_R_SAME_WORKFLOW_TREE_NEW_BRANCH_EVENT_V1','exact_jst':now(),
        'workflow_tree':wf['tree'],'prior_audit_member':'bridge_work/evidence/WORKFLOW_TRIGGER_CHECK.json',
        'prior_audit_sha256':sha(INPUT/'bridge_work/evidence/WORKFLOW_TRIGGER_CHECK.json'),
        'new_branch':BRANCH,'new_paths':wf['paths'],'workflow_N':353,'push_matches':[],
        'same_tree_actual_git_verified':True,'new_event_evaluation':wf['records'],
        'skip_ci_alone_proof':False,'PR_created':False,'dispatches':0,'cancels':0})
    checkpoint('P0','SPEC_SOURCE_DESIGN_FIXED',{'input_roles':len(ROLES),'payload_member_verified':298,
        'directive_exact':True,'workflow_push_matches':0},'Commit P0, actual GET; then reuse certificates and pure native saved-case comparison')
    print(json.dumps({'status':'P0_READY_FOR_COMMIT','policy_sha256':sha(OUT/'DIRECTIVE.txt'),'input_binding_sha256':sha(OUT/'INPUT_BINDING.json')}))

if __name__=='__main__': main()
