"""Contract and saved-metadata tests only. No Risk model runtime or scoring."""
import ast
import copy
import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts import audit_phase57_msh_entry_v2_1_predevelopment as a


class SeparateAxisContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=a.read(a.ROOT/a.CONTRACT)

    def reject(self,path,value):
        c=copy.deepcopy(self.c);node=c
        for key in path[:-1]:node=node[key]
        node[path[-1]]=value
        with self.assertRaises((ValueError,KeyError),msg=str(path)):
            a.validate_contract(c)

    def test_full_static_audit_sources_and_saved_metadata(self):
        report,plan,ledger=a.audit()
        e=a.ROOT/a.EVIDENCE
        self.assertEqual(report,a.read(e/'static-audit.json'))
        self.assertEqual(plan,a.read(e/'split-metadata.json'))
        self.assertEqual(ledger,a.read(e/'risk-universe-ledger.json'))
        self.assertEqual(report['sourcePinsVerified'],100)
        self.assertEqual((report['riskAnchors']['rows'],report['riskAnchors']['labelable']), (277,181))
        self.assertEqual(len(plan['replicas']),24)
        self.assertEqual(plan['outerRiskAnchors'],232)
        self.assertFalse(report['modelRuntimeImported'])
        self.assertFalse(any(report['counters'].values()))

    def test_artifact_manifest_and_contract_byte_seal(self):
        e=a.ROOT/a.EVIDENCE
        self.assertEqual(a.sha(e/'manifest.json'),(e/'manifest.sha256').read_text().strip())
        for p,h in a.read(e/'manifest.json')['artifactPins'].items():
            self.assertEqual(a.sha(a.ROOT/p),h,p)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);p=root/a.CONTRACT;p.parent.mkdir(parents=True)
            p.write_bytes((a.ROOT/a.CONTRACT).read_bytes()+b' ')
            (root/(a.CONTRACT+'.sha256')).write_text(a.sha(p)+'\n')
            with self.assertRaisesRegex(ValueError,'CONTRACT_HASH'):a.audit(root)

    def test_frozen_identities_cannot_be_relabelled(self):
        for key in a.IDENTITIES:self.reject(['identity',key],'0'*64)
        self.reject(['opportunityAxis','threshold'],1.9)
        self.reject(['opportunityAxis','modelRefit'],True)

    def test_risk_only_and_full_replacement_rejected(self):
        self.reject(['architecture','riskOnlyEntry'],True)
        self.reject(['architecture','fullReplacement'],True)
        self.reject(['architecture','newPrimaryModelCount'],2)
        self.reject(['architecture','scope'],'FULL_REPLACEMENT')

    def test_v1_shadow_anchor_is_independent_of_future_labels(self):
        rows=[{'selectorEventId':f'e{i}','symbolSessionId':'s|date','decisionTimestamp':f'2024-09-17T{t}:00+09:00',
               'label':{'labelable':False,'futureMAE':-100}} for i,t in enumerate(['09:30','10:00','10:30'])]
        saved={'e0':{'expectedClass':1.9,'state':'SKIP_THIS_DECISION','reason':'BELOW_FROZEN_THRESHOLD'},
               'e1':{'expectedClass':2.,'state':'ENTER','reason':'FIRST_QUALIFYING_DECISION'},
               'e2':{'expectedClass':3.,'state':'SKIP_THIS_DECISION','reason':'ALREADY_ENTERED'}}
        before=[r['selectorEventId'] for r in a.shadow_anchor_audit(rows,saved)]
        for r in rows:r['label']={'labelable':True,'futureMAE':0,'futureMFE':999}
        self.assertEqual(before,[r['selectorEventId'] for r in a.shadow_anchor_audit(rows,saved)])
        self.assertEqual(before,['e1'])
        saved['e2']['state']='ENTER'
        with self.assertRaisesRegex(ValueError,'FROZEN_V1_STATE_PARITY'):a.shadow_anchor_audit(rows,saved)

    def test_risk_skip_cannot_enable_later_entry_or_wait(self):
        for key in ['wait','expiry','retryAfterRiskReject','v1SkipRecovery','entryTimingChange']:
            self.reject(['state',key],True)
        self.reject(['state','anchorConsumption'],'RISK_ENTER_CONSUMES_ONLY')
        self.reject(['state','outputs'],['ENTER','WAIT','SKIP_THIS_DECISION'])

    def test_training_universe_not_raw_qualified_or_portfolio_subset(self):
        for n in [353,181,173,3800]:self.reject(['universe','riskAnchorCount'],n)
        self.reject(['universe','labelAvailabilityInRuntimeEligibility'],True)
        self.reject(['universe','fullLiveUniversePITClaim'],True)
        self.reject(['trainingRows','symbolSpecificOverrides'],True)
        self.reject(['trainingRows','weightFormula'],'PNL_WEIGHTED')

    def test_censored_anchors_are_retained_without_zero_labels(self):
        rows=a.read(a.ROOT/a.EVIDENCE/'risk-universe-ledger.json')
        unknown=[r for r in rows if not r['labelable']]
        self.assertEqual(len(unknown),96)
        self.assertEqual({x:sum(r['censorReason']==x for r in unknown) for x in ['PROVIDER_GAP','LUNCH_BREAK','SESSION_END']},
                         {'PROVIDER_GAP':51,'LUNCH_BREAK':25,'SESSION_END':20})
        self.assertTrue(all(r['v1Anchor'] and r['trainingLabelStatus']=='EXCLUDED_TRAINING_LOSS_ONLY' for r in unknown))
        self.assertTrue(all('D30' not in r and 'predictedD30' not in r for r in rows))

    def test_four_inputs_exclude_opportunity_future_and_raw_price(self):
        for extra in ['ridgeScore','ridgeRank','expectedClass','futureMFE','futureMAE','symbol','decisionPrice','futureExitPnl']:
            self.reject(['features','order'],[extra]+a.ORDER[1:])
        for key in ['selectorScoreInsideRisk','selectorRankInsideRisk','v1ScoreInsideRisk','featureInteractions','polynomials']:
            self.reject(['features',key],True)
        self.reject(['features','activeOptionalFeatures'],['timeOfDay'])

    def test_missing_and_fold_scaling_contract(self):
        for key in ['missingIsZero','forwardFill','futureFill','nextObservationFill','interpolation','outcomeDerivedImputation','volumeMissingAsZero']:
            self.reject(['missing',key],True)
        self.reject(['missing','scaledRawPredictors'],a.ORDER)
        self.reject(['missing','unscaledIndicators'],[])

    def test_d30_ridge_regularization_and_capacity(self):
        for key,value in [('soleEnterGate',True),('binaryTailTarget',True),('clipping',True),('horizonMinutes',60),('missingExpectedBar','FILL')]:
            self.reject(['target',key],value)
        for key,value in [('family','XGBOOST'),('lambda',.01),('modelCount',2),('featureCount',5),('solver','GRID_SEARCH'),('minRows',2)]:
            self.reject(['model',key],value)

    def test_chronological_and_symbol_split_leakage_protection(self):
        self.reject(['cv','folds',0,'evaluationOrdinals'],[16,31])
        self.reject(['cv','folds',0,'innerFitOrdinals'],[1,16])
        self.reject(['cv','fitStatisticsFromEvaluation'],True)
        self.reject(['trainingRows','sameSymbolSessionAcrossTrainEval'],True)
        for k in ['heldGroupOutcomesUsedForThreshold','postHocRebalancing']:
            self.reject(['crossSymbol',k],True)
        plan=a.read(a.ROOT/a.EVIDENCE/'split-metadata.json')
        groups=[set(g['symbols']) for g in plan['groups']]
        self.assertEqual(len(set.union(*groups)),sum(map(len,groups)))
        for g in plan['groups']:
            self.assertTrue(all(a.symbol_group(s)==g['group'] for s in g['symbols']))
        self.assertTrue(all(r['purgedByBoundaryCount']==r['heldSymbolLeakCount']==r['symbolSessionOverlap']==0 for r in plan['replicas']))

    def test_threshold_selection_and_all_numeric_gates_sealed(self):
        self.reject(['decision','thresholdCandidatesPct'],[1,1.5,2,5,10])
        self.reject(['decision','selectionOrder'],['MINIMUM_MEAN_D30'])
        for k in ['opportunityTierThresholds','opportunityRiskProduct','positionSizingUsesScore','fallbackToV1']:
            self.reject(['decision',k],True)
        for section in ['primary','guardrails','crossSymbol']:
            for key,value in self.c['numericGates'][section].items():
                self.reject(['numericGates',section,key],value+1)
        self.reject(['metrics','primaryPreservation'],'V2_ORIGINAL_SELECTOR_WINDOW')

    def test_execution_portfolio_and_fair_comparator_boundaries(self):
        self.reject(['executionQuality','role'],'LOW_PRICE_GATE')
        self.reject(['portfolio','role'],'PRIMARY_RETURN_GATE')
        for k in ['fabricatedLiquidationAllowed','engineChangesAllowed']:self.reject(['portfolio',k],True)
        for k,v in [('exit','FIXED12'),('allocation','RANK'),('initialCashJpy',2000000),('lotSize',1),
                    ('roundTripCostPctOfEntryNotional',0),('maximumConcurrentPositions',3)]:
            self.reject(['fairComparator',k],v)

    def test_all_counter_safety_and_authorization_boundaries(self):
        for k in self.c['currentScopeCounters']:self.reject(['currentScopeCounters',k],1)
        for k in a.SAFETY:self.reject(['safety',k],True)
        for k in ['trainingAuthorizedByThisContractFreeze','newProviderRequestsAllowed']:
            self.reject(['dataProtection',k],True)
        self.reject(['repository','mainMergeAllowed'],True)

    def test_audit_has_no_model_prediction_or_provider_import(self):
        tree=ast.parse(Path(a.__file__).read_text());modules=set()
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):modules.update(x.name.split('.')[0] for x in n.names)
            if isinstance(n,ast.ImportFrom):modules.add(n.module.split('.')[0])
            if isinstance(n,ast.Call):
                name=n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id if isinstance(n.func,ast.Name) else ''
                self.assertNotIn(name,{'fit','predict','predict_proba','decide','replay','solve','exec','eval','__import__'})
        self.assertLessEqual(modules,{'argparse','collections','datetime','gzip','hashlib','json','math','pathlib'})


if __name__=='__main__':
    unittest.main(verbosity=2)
