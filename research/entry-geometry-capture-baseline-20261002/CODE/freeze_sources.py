#!/usr/bin/env python3
"""Read saved originals, verify identity, and freeze descriptive scope. No policy execution."""
import collections, gzip, hashlib, json, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'research/entry-geometry-capture-baseline-20261002'
SCRATCH = ROOT.parent
HEAD = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def read(p):
    b=Path(p).read_bytes()
    return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,o):
    (OUT/name).write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def blob(p):
    s=subprocess.check_output(['git','ls-tree',HEAD,'--',p],cwd=ROOT,text=True).strip()
    return s.split()[2] if s else None
def source(name,p,expected=None,manifest=None,pop=None,origin=None):
    p=Path(p);rel=str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
    actual=sha(p); gitsha=blob(rel) if p.is_relative_to(ROOT) else None
    oid=hashlib.sha1(b'blob '+str(p.stat().st_size).encode()+b'\0'+p.read_bytes()).hexdigest()
    assert expected is None or expected==actual,(name,'SHA256_MISMATCH',expected,actual)
    assert gitsha is None or gitsha==oid,(name,'GIT_BLOB_MISMATCH')
    return dict(name=name,path=rel,git_blob_sha=gitsha,computed_git_object_sha1=oid,sha256=actual,
                expected_sha256=expected,hash_authority=manifest,hash_status='PASS',source_head=origin or HEAD,
                available_at_head=HEAD,bytes=p.stat().st_size,population_N=pop,
                exposure_status='SAVED_ALREADY_EXPOSED_DEVELOPMENT',known=True,
                unknown_note='Git blob is null for artifact-only members; computed object identity is separately labeled' if gitsha is None else None)

opp_path=ROOT/'docs/evidence/phase57-entry-timing-signal-census-v1/measurement/opportunity-records.json.gz'
imm_path=ROOT/'docs/evidence/phase57-state-conditioned-signal-entry-v1/measurement/baseline-immediate-records.json.gz'
raw_path=ROOT/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/raw-paths-evaluator-only.json.gz'
state_path=ROOT/'docs/evidence/phase57-state-v3-9pattern-entry-v1/measurement/state-checkpoints.json.gz'
r1_path=SCRATCH/'saved_artifacts/all-material-r1/ci-run-a/entry-records.json.gz'
orig_path=ROOT/'docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz'
opp,imm,r1,raw,oldstate=map(read,[opp_path,imm_path,r1_path,raw_path,state_path])
orig=[json.loads(x) for x in gzip.open(orig_path,'rt') if x.strip()]
ids=[x['opportunity'] for x in opp]
assert len(ids)==len(set(ids))==2155
assert set(ids)=={x['opportunity'] for x in imm}=={x['opportunity'] for x in r1}
assert all(x['sourceHash']==raw[x['opportunity']]['sourceHash'] for x in opp)
ob={x['opportunity']:x for x in opp}
for records in [imm,r1]:
    assert len(records)==len({x['opportunity'] for x in records})==2155
    for x in records:
        o=ob[x['opportunity']]
        assert x['session']==o['session'] and x['symbol']==o['symbol']
        assert x['quality']['selectorPrice']==o['selectorPrice']
        assert x['opportunity']==x['session']+'|'+x['symbol']
        assert (x['entryMinute'] is None)==(x['entryId'] is None)==(x['price'] is None)
        if x['entryId']:assert x['entryId']==x['opportunity']+'|'+str(x['entryMinute'])
assert len(orig)==3800 and len({x['sessionDate'] for x in orig})==76
assert len({x['decisionTimestamp'] for x in orig})==760
assert set(collections.Counter(x['decisionTimestamp'] for x in orig).values())=={5}
assert set(collections.Counter(x['sessionDate'] for x in orig).values())=={50}
freeze=read(ROOT/'docs/evidence/phase57-entry-all-material-v1/ENTRY_DUAL_FREEZE_R10.json')
assert freeze['decision']['retain']==['IMMEDIATE','ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF']
sources=[]
for name,p,mp,key,n in [
    ('canonical_opportunities',opp_path,opp_path.parent/'manifest.json',opp_path.name,2155),
    ('immediate_entry_records',imm_path,imm_path.parent/'manifest.json',imm_path.name,2155),
    ('saved_raw_path_evaluator_only',raw_path,raw_path.parent/'manifest.json',raw_path.name,len(raw)),
    ('legacy_state_v3_9pattern',state_path,state_path.parent/'manifest.json',state_path.name,len(oldstate))]:
    m=read(mp);sources.append(source(name,p,m[key],str(mp.relative_to(ROOT)),n))
sources.append(source('r1_frozen_entry_records',r1_path,freeze['allMaterialR1']['entryRecordsSHA256'],
    'ENTRY_DUAL_FREEZE_R10.json + artifact10851958443 + CI_RECEIPT.json',2155,freeze['allMaterialR1']['workflowHead']))
loc=read(ROOT/'docs/evidence/phase57-entry-location-study/protocol.json')
sources.append(source('original_selector_3800',orig_path,loc['sourcePins'][str(orig_path.relative_to(ROOT))],
    'phase57-entry-location-study/protocol.json',3800))
sources.append(source('original_selector_development_receipt',ROOT/'docs/evidence/phase57-long-only-frozen-selector-v1-development-evidence.json'))
sources.append(source('C0_population_and_original_split_receipt',OUT/'CHECKPOINT_00_CURRENT_STATE.md'))
sources.append(source('dual_entry_freeze',ROOT/'docs/evidence/phase57-entry-all-material-v1/ENTRY_DUAL_FREEZE_R10.json'))
art=[]
for q in SCRATCH.glob('attachments/*/*.zip'):
    expected=freeze['allMaterialR1']['artifactDigest'].split(':')[1] if q.name=='All_Material_R1_Frozen.zip' else freeze['immediate']['canonicalEvaluatorArtifactDigest'].split(':')[1]
    assert sha(q)==expected
    art.append(dict(path=str(q),artifact_id=10851958443 if q.name=='All_Material_R1_Frozen.zip' else 10818327246,sha256=sha(q),bytes=q.stat().st_size,expected_sha256=expected,hash_status='PASS'))
for s in sources:
    if s['name'] in ('canonical_opportunities','immediate_entry_records','r1_frozen_entry_records'):
        s.update(sessions=58,symbols=950)
    elif s['name']=='original_selector_3800':s.update(sessions=76,symbols=934)
    else:s.update(sessions=None,symbols=None)
(OUT/'FROZEN_ARTIFACT_MEMBERS').mkdir(exist_ok=True)
shutil.copyfile(r1_path,OUT/'FROZEN_ARTIFACT_MEMBERS/R1_ENTRY_RECORDS.original.json.gz')
write('SOURCE_MANIFEST.json',dict(status='C1_SOURCE_IDENTITY_PASS',basis_head=HEAD,sources=sources,artifacts=art,
    source_identity_mismatches=0,policy_executions=0,
    source_roles={'selector_timestamp':'canonical selectorMinute + session, exact JST',
      'selector_price':'canonical selectorPrice (cross-checked with both saved Entry quality.selectorPrice)',
      'global_low_high_timestamps':'not stored as canonical global extrema in Entry records; mechanical saved-path calculation required',
      'legacy_oracle':'orderedOracle is MAXIMUM_STRICTLY_ORDERED_LOW_TO_HIGH_REBOUND, not global low/high',
      'entry_mae_mfe':'saved labels.maeEnd/mfeEnd plus labels.30/60',
      'State9_RC2':'NOT_AVAILABLE_WITH_CERTIFIED_EXACT_SOURCE_JOIN; legacy State-v3 is not RC2'},
    calendar={'timezone':'Asia/Tokyo','AM':[540,690],'PM':[750,930],'lunch_excluded_minutes':60,
      'regular_close_before_2024_11_05':900,'regular_close_after':930,
      'canonical_current_window':'2025 canonical source, includes saved reconciled terminal marks; no new auction/daily supplementation',
      'unknown_intrabar_order':'bars at identical timestamps cannot prove High/Low within-bar chronology'}))
days=sorted({x['session'] for x in opp});symbols=sorted({x['symbol'] for x in opp})
write('POPULATION_FREEZE.json',dict(status='CANONICAL_2155_FROZEN',N=2155,sessions_N=58,symbols_N=950,
    opportunity_ids=ids,sessions=days,symbols=symbols,
    opportunity_ids_sha256=hashlib.sha256(json.dumps(ids,separators=(',',':')).encode()).hexdigest(),
    arms=freeze['decision']['retain'],additional_arms=[],duplicates=0,
    original_selector=dict(N=3800,sessions_N=76,decision_timestamps_N=760,top5=5,decisions_per_session=10,
      decision_times=['09:30','10:00','10:30','11:00','11:30','13:00','13:30','14:00','14:30','15:00'],
      split_counts={'TRAIN':38,'VALIDATION':19,'DEVELOPMENT_TEST':19},
      split_count_authority='C0 saved receipt; counts verified present there, underlying split membership not used here',
      separate_lineage=True,NOT_the_current_2155_denominator=True),
    lineage_note='Original76-session selector receipts and later All-Material current2155/58-session Entry population are distinct saved populations. No 3800-to2155 arbitrary truncation or pooling. Frozen Entry Dual R10 is primary authority.',
    primary_exposure='All2155 were already outcome-exposed Development; old evaluation labels are descriptive reused evidence, not newly opened validation/OOS',
    new_partition_open=0))
write('JOIN_KEY_CONTRACT.json',dict(primary=['opportunity'],opportunity_format='session|symbol',
    exact_checks=['session','symbol','selectorMinute','selectorPrice','entryId','entryMinute','price','sourceHash'],
    row_unit='one opportunity per arm; arms paired, no independent sample duplication',
    mismatch_action='retain JOIN_MISMATCH row with null metrics and stop on unresolved source/time contradiction',
    no_entry='explicit row retained',unknown='null + reason; never zero fill',
    state_join='Only exact timestamp/session/security/source/semantic revision; no new State generation or silent legacy-to-RC2 substitution'))
(OUT/'C1_AUDIT.md').write_text('''# 🔒 C1 Source / Population Audit\n\nStatus: C1_SOURCE_IDENTITY_PASS\n\n- Canonical population: 2,155 unique opportunities / 58 sessions / 950 symbols. Both saved Entry arms cover exactly the same IDs. Raw source hashes and Selector prices match on all 2,155.\n- Original Frozen Selector: 3,800 rows / 760 timestamps / 76 sessions; Top5 and 10 decisions per session independently counted. Original split counts 38/19/19 are present in C0; split membership is not used in this later population.\n- Original76 and current2155 are different historical Development lineages. No arbitrary matching or pooling.\n- R1 artifact and Entry member match the authoritative Dual Freeze SHA-256. IMMEDIATE artifact digest and manifest hashes pass.\n- Existing orderedOracle is the largest strictly ordered rebound, not the global extrema. Its fields will remain preserved. Saved labels cannot supply true global-low time or a fresh maximum strictly after every Entry: C2 will pin mechanical arithmetic from saved raw paths. No policies or labels are regenerated.\n- Current MAE/MFE remain the saved canonical signed metrics. Intrabar ordering cannot be inferred. Historical fill proxy and source completeness limitations remain.\n- Final RC2 State9 cannot yet be certified against these exact Entry source identities. Legacy State-v3 nine-pattern records are preserved with their actual revision, not called final State9. Optional RC2 panel may be NOT_AVAILABLE.\n- All forbidden activity counters remain zero.\n''')
print(json.dumps({'status':'C1_SOURCE_IDENTITY_PASS','N':2155,'sessions':58,'symbols':950,'hash_mismatch':0,'original_N':3800}))
