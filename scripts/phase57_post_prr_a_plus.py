"""Append-only, saved-outcome Phase A+ descriptive reader. No policy or fit imports."""
from __future__ import annotations

import collections
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/evidence/phase57-post-prr-phase-a'
OUT = ROOT / 'docs/evidence/phase57-post-prr-phase-a-plus/cycle-20260929-01'
OUT.mkdir(parents=True, exist_ok=True)
HANDOFF = ROOT.parent / 'upload/Ark_Terminal_Phase_A_Plus_State_Signal_Integrated_Work_20260929(1).md'

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(name, value):
    path = OUT/name
    if path.exists(): raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n')
def read(name): return json.loads((BASE/name).read_text())
def rows(name):
    with gzip.open(BASE/name,'rt') as f: return [json.loads(line) for line in f]
def write_rows(name, iterable):
    path=OUT/name
    if path.exists(): raise FileExistsError(path)
    raw=''.join(json.dumps(r,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n' for r in iterable).encode()
    path.write_bytes(gzip.compress(raw,mtime=0))
def D(x): return None if x is None else Decimal(str(x))
def S(x): return None if x is None else str(x)

def precommit():
    manifest=read('MANIFEST.json')
    for name,h in manifest['fileSha256'].items():
        if sha(BASE/name)!=h: raise AssertionError(('BASE_MANIFEST_DRIFT',name))
    for name,h in manifest['scriptSha256'].items():
        if sha(ROOT/name)!=h: raise AssertionError(('BASE_SCRIPT_DRIFT',name))
    source={name:sha(BASE/name) for name in manifest['fileSha256']}
    write('START_AUDIT.json',{'schema':'phase57-a-plus-start-v1','basisHead':'c70b981fd07128dfd9b18893b4aca3a387d17e3b','pr':587,'prState':'OPEN_DRAFT_UNMERGED','actionsAtBasisHead':[],'phaseAManifestSha256':sha(BASE/'MANIFEST.json'),'phaseAFileCount':len(source),'instructionSha256':sha(HANDOFF),'upstreamBinaryAvailability':'SPARSE_CHECKOUT_NOT_PRESENT; connector binary decode unsupported; inspect dependency-specific blocks','previousPhaseAClosure':'PHASE_A_COMPLETE_NEXT_EXPERIMENT_SPEC_DRAFT_ONLY'})
    write('SOURCE_MANIFEST.json',{'basisHead':'c70b981fd07128dfd9b18893b4aca3a387d17e3b','phaseAFileSha256':source,'priorSourcePins':read('START_AUDIT.json')['sourcePins'],'sourceLevel':{'phaseA':'SAVED_ROWS_RECALCULATION','CCMG/PRR upstream binary':'MANIFEST_HASH_PIN_ONLY_UNLESS_RECOVERED'},'instructionSha256':sha(HANDOFF)})
    write('A_PLUS_PRECOMMIT.json',{'schema':'phase57-a-plus-precommit-v1','basisHead':'c70b981fd07128dfd9b18893b4aca3a387d17e3b','instructionSha256':sha(HANDOFF),'phaseAManifestSha256':sha(BASE/'MANIFEST.json'),'scope':['intent I/E/K with unknown preserved','same-mask accounting and world decomposition','fixed five upside bands','both-sided tail and all-session/all-symbol LOO','session-cluster descriptive bootstrap','rank versus delta and missingness','saved as-of State/Signal inventory, only provable features','intent-to-fill reference and remaining-upside only when path exists','branch equivalence and stage2 lineage audit','draft experiment and independent calculation'],'populationStart':'ACCOUNTING_RECONCILIATION_ROWS.jsonl.gz 1725; key=(world,arm,entryId)','moneyFormula':'Decimal; deltaJPY=q*(ccmgExitPrice-controlExitPrice); deltaNetPP=100*deltaJPY/entryCostJpy; null stays null','analysisExposure':'Phase A A1 outcome and reports have already been viewed; no independent validation claim','prohibitions':{'newFits':0,'newPolicyReplays':0,'newProviderRequests':0,'protectedPartitionOpenings':0,'externalLlmRequests':0,'orders':0,'mainMerges':0},'selection':None,'productionReady':False,'experimentAuthorized':False})
    (OUT/'A_PLUS_PRECOMMIT.sha256').write_text(sha(OUT/'A_PLUS_PRECOMMIT.json')+'  A_PLUS_PRECOMMIT.json\n')
    print('PRECOMMIT',sha(OUT/'A_PLUS_PRECOMMIT.json'))

def inventory():
    accounting=rows('ACCOUNTING_RECONCILIATION_ROWS.jsonl.gz')
    mask=rows('COMPARISON_MASK_ROWS_INTENT_V2.jsonl.gz')
    paired=rows('A1_PAIRED_ROWS.jsonl.gz')
    assert len(accounting)==len(mask)==1725 and len(paired)==1525
    am={(r['world'],r['arm'],r['entryId']):r for r in accounting}
    mm={(r['world'],r['arm'],r['entryId']):r for r in mask}
    assert len(am)==len(mm)==1725 and set(am)==set(mm)
    for k in am:
        a,m=am[k],mm[k]
        for col in ('session','symbol','entryMinute','entryPrice','quantity','routeDecision','primary'):
            assert a[col]==m[col], (k,col)
        assert m['paired_outcome_known']==(a['deltaPnlJpy'] is not None)
    schema={n:{'rows':len(rs),'columns':sorted(set().union(*(set(r) for r in rs))),'sha256':sha(BASE/n)} for n,rs in [('ACCOUNTING_RECONCILIATION_ROWS.jsonl.gz',accounting),('COMPARISON_MASK_ROWS_INTENT_V2.jsonl.gz',mask),('A1_PAIRED_ROWS.jsonl.gz',paired)]}
    write('SCHEMA_MAP.json',{'schema':'phase57-a-plus-schema-v1','files':schema,'key':['world','arm','entryId'],'source':str(BASE.relative_to(ROOT)),'notes':['causalGuardTraceAtIntent is boolean, not values','fold is in accounting rows','A1_PAIRED_ROWS intentOrder is superseded by corrected V2 mask']})
    # Source and availability are catalogued before new feature/outcome associations.
    features=[
      ('entryMinute','accounting','A','at Entry','clock minute in JST day'),
      ('ccmgFirstIntentMinute','accounting','A','at intent','clock minute; not a fill'),
      ('entryPrice','accounting','A','at Entry','effective Entry includes buy cost'),
      ('routeDecision','accounting','A','at Entry','frozen 2-head decision'),
      ('score5/score10','accounting','A','at Entry','frozen OOF; nested stage2 lineage separate'),
      ('causalGuardTraceAtIntent','corrected mask','A','at intent','presence boolean only'),
      ('runtime_feature_asof_valid','corrected mask','A','at intent','guard as-of boolean only'),
      ('certified milestone / HWM / floor margin / confirmation / fresh price / knownAt','CCMG dry trace','C','intended at intent','SOURCE_MISSING_BINARY_FOR_ROW_JOIN'),
      ('causal State vocabulary','checkpoint market snapshot or definition','C','intended at intent','SOURCE_MISSING_BINARY_FOR_ROW_JOIN'),
      ('Continuation / Breakout / Compression-Expansion / Higher Low-Swing Recovery / Wick-Close Recovery / VWAP-Level Reclaim','checkpoint signal snapshot or saved bars','C','intended at intent','SOURCE_MISSING_BINARY_FOR_ROW_JOIN'),
      ('post-intent high/low','owned path','C','evaluator only','SOURCE_MISSING_BINARY_AND_LABEL_ENDPOINT_UNVERIFIED')]
    write('STATE_SIGNAL_AVAILABILITY.json',{'schema':'phase57-a-plus-feature-availability-v1','features':[dict(featureId=x[0],source=x[1],availabilityClass=x[2],asof=x[3],reasonOrLimit=x[4]) for x in features],'rowCoverageFromSavedMask':{arm:{'intentN':sum(m['world']=='ALL_100' and m['arm']==arm and m['has_ccmg_first_intent'] for m in mask),'causalGuardTracePresenceN':sum(m['world']=='ALL_100' and m['arm']==arm and m['causalGuardTraceAtIntent'] for m in mask),'fullStage2RuntimeSnapshotN':sum(m['world']=='ALL_100' and m['arm']==arm and m['fullStage2RuntimeFeatureSnapshot'] for m in mask)} for arm in ('IM','R1')},'noNewFeatureOutcomeAssociationYet':True})
    write('PRIOR_STATE_SIGNAL_USAGE_AUDIT.json',{'schema':'phase57-a-plus-prior-state-v1','historicSource':'project_sources/06-txt (2026-09-21 historical handoff); scripts/phase57_exit_checkpoints_v1.py::canonical_recognition (textual GitHub source at basis HEAD)','families':['Continuation','Breakout','Compression→Expansion','Higher Low–Swing Recovery','Wick–Close Recovery','VWAP–Level Reclaim'],'historicEntrySignalCensus':'DONE; T0 UNKNOWN 58.9%; fallback dependence 90.8% in prior Entry study; EXIT first-intent effect not implied','checkpointRecognition':'static code calls phase57_state_v3_9pattern_entry_v1.classify_state_v3 and phase57_entry_timing_signals.detect; saved row-level snapshot at this scope not available','CCMG':'separate guard milestone/floor/breach state; no proof that general State/6 signal families used in CCMG decision','PRR':'frozen Potential rank route, not State-vocabulary gate','versionHashes':{'scripts/phase57_exit_checkpoints_v1.py':'a2248ffb6ad1c5259f9d768ec570aee74b095865'},'pastClosures':'Phase A and predecessor closures remain unchanged','unverified':['each historic signal definition hash and newer replacement status','row-level existing State/Signal snapshot with knownAt','runtime suitability at first intent']})
    write('CAUSAL_FEATURE_PLAN.json',{'schema':'phase57-a-plus-causal-feature-plan-v1','allowed':'as-of join if source ID, barEnd and knownAt <= first intent; or fixed pure deterministic historical source with suffix invariance','blockedAtThisSnapshot':['guard trace binary absent','saved market State/signal rows absent','no permitted price path to recreate signals','no future label or exit price as runtime input'],'role':'metadata inventory and supported Entry/clock/rank values only; no State×delta association on absent values','requiredMetadata':['feature_id','definition_hash','source_file_hash','source_row_ids','bar_end','knownAt','availability_class','inference_role'],'causalTestsPending':['input truncated to tau','future suffix invariance','closed bar','swing recognition knownAt','lunch/session','no policy/provider/fit import']})
    source=[{'name':n,'sha256':sha(BASE/n),'rows':len(rs)} for n,rs in [('ACCOUNTING_RECONCILIATION_ROWS.jsonl.gz',accounting),('COMPARISON_MASK_ROWS_INTENT_V2.jsonl.gz',mask),('A1_PAIRED_ROWS.jsonl.gz',paired)]]
    write('INVENTORY_FREEZE.json',{'schema':'phase57-a-plus-inventory-freeze-v1','sources':source,'schemaMapSha256':sha(OUT/'SCHEMA_MAP.json'),'availabilitySha256':sha(OUT/'STATE_SIGNAL_AVAILABILITY.json'),'intentPopulation':{'all100':1614,'fundedAdditionalWorldRows':111},'analysisExposure':'prior A1 viewed; availability inventory before new associations'})
    spec={'schema':'phase57-a-plus-analysis-spec-v1','inventorySha256':sha(OUT/'INVENTORY_FREEZE.json'),'population':'1725 accounting/mask join; paired K outcome-side; I firstSellIntent not null; E first intent < control decision and as-of boolean true, with branch-equivalence limitation','groups':['ALL_100','PRIMARY_100','PRIMARY_FUNDED','PRIMARY_OUTSIDE_100'],'bands':['<1','[1,3)','[3,5)','[5,10)','[10,inf)','UNKNOWN'],'bandValue':'futureUpsidePctEvaluatorOnly; Decimal(str(value))','comparisons':['CCMG-R50','frozen route-R50'],'money':'Decimal(q)*[Decimal(str(ccmgExitPrice))-Decimal(str(controlExitPrice))]; netPP=100*delta/entryCostJpy','tail':'gross gain/loss separate; top1/3/5/10; tie by stable (world,arm,entryId)','LOO':'all 24 sessions and every symbol, both sides','bootstrap':{'cluster':'session','sessionList':'ascending union of ALL_100 sessions','seed':20260929,'generator':'numpy.PCG64','B':10000,'draw':'24 sessions with replacement, shared across worlds/arms/comparisons','CI':'95% percentile linear interpolation h=(Bvalid-1)*p','uncomputable':'null, do not redraw'},'rank':['score5','score10','rank5Decile','rank10Decile'],'rankScopes':['all paired','I∩K','E∩K'],'stateAssociation':'BLOCKED if source values/knownAt absent; do not substitute guard boolean','featureFamilies':['guard milestone/HWM/floor/confirmation/gap','existing causal State vocabulary','six existing signal families','frozen Potential ranks'],'noThresholdOptimization':True}
    write('ANALYSIS_SPEC.json',spec)
    (OUT/'ANALYSIS_SPEC.sha256').write_text(sha(OUT/'ANALYSIS_SPEC.json')+'  ANALYSIS_SPEC.json\n')
    print('INVENTORY_SPEC',sha(OUT/'ANALYSIS_SPEC.json'))

if __name__=='__main__':
    import sys
    if sys.argv[1:] == ['precommit']: precommit()
    elif sys.argv[1:] == ['inventory']: inventory()
    else: raise SystemExit('usage: phase57_post_prr_a_plus.py precommit|inventory')
