import unittest
from pathlib import Path
import sys
from datetime import date,timedelta

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from preopen_reference_admission import reference_dependencies,enforce_reference_admission
from preopen_selector import PreopenError
from preopen_selector import digest
from preopen_io import SAFE_FLAGS, write_json
from tempfile import TemporaryDirectory


class ReferenceAdmission(unittest.TestCase):
    def test_reference_is_prior_only_and_protected_gap_limits_suffix(self):
        start=date(2024,1,1)
        calendar=[(start+timedelta(days=i)).isoformat() for i in range(100)]
        target=calendar[90]
        out=reference_dependencies({'fit':[target]},calendar,[calendar[50]],minimum_bars=76)
        row=out['rows'][0]
        self.assertNotIn(target,row['referenceDates'])
        self.assertEqual(len(row['referenceDates']),76)
        self.assertEqual(row['comparableSuffixUpperBound'],39)
        self.assertEqual(out['conflictDates'],[calendar[50]])

    def test_market_gate_rejects_before_any_raw_source_is_needed(self):
        calendar=['2024-10-01','2024-10-02','2024-10-03']
        request={'mode':'AUTHORIZED_DEVELOPMENT','exchangeSessions':calendar,
                 'protectedReferenceSessions':['2024-10-01']}
        with self.assertRaisesRegex(PreopenError,'PROTECTED_REFERENCE_CONFLICT'):
            enforce_reference_admission(request,{'exactSplits':{'fit':['2024-10-02']}})
        # No file/price provider/model object is supplied or opened by this gate.
        self.assertEqual(enforce_reference_admission({**request,'mode':'SYNTHETIC'},
            {'exactSplits':{'fit':['2024-10-02']}}),None)

    def test_unprotected_new_listing_does_not_require_price_filling(self):
        calendar=['2024-10-01','2024-10-02','2024-10-03']
        audit=enforce_reference_admission({'mode':'AUTHORIZED_DEVELOPMENT',
            'exchangeSessions':calendar,'protectedReferenceSessions':[]},
            {'exactSplits':{'fit':['2024-10-02']}})
        self.assertEqual(audit['conflictDates'],[])
        self.assertEqual(audit['rows'][0]['comparableSuffixUpperBound'],1)

    def test_explicit_four_day_approval_preserves_seal_and_teacher_hash(self):
        with TemporaryDirectory() as tmp:
            dates=['2024-09-10','2024-09-11','2024-09-12','2024-09-13']
            admission={'exactSplits':{'fit':['2024-10-02']},'ledgerSha256':'a'*64}
            approval={'schema':'ARK_APPROVED_DAILY_HISTORY_EXCEPTION_V1','approved':True,
                'sourceKind':'DIRECT_USER_MESSAGE','ownerStatement':'approved','authorizedAt':'2026-10-14T11:23:47+09:00',
                'workId':'test','dataset':'DAILY_RAW','allowedUse':'CAUSAL_PRICE_HISTORY_ONLY',
                'dates':dates,'splitHash':digest(admission['exactSplits']),
                'originalLedgerSha256':admission['ledgerSha256'],'originalLedgerRewrite':False,
                'freshCredit':False,'teacherDatesAdded':0,'outcomeEvaluationAllowed':False,**SAFE_FLAGS}
            entry=write_json(Path(tmp)/'approval.json',approval)
            request={'mode':'AUTHORIZED_DEVELOPMENT','exchangeSessions':dates+['2024-10-02'],
                'privateRoot':tmp,'reuseWorkId':'test','protectedReferenceSessions':dates,
                'historyReferenceException':entry}
            original_hash=digest(admission)
            audit=enforce_reference_admission(request,admission)
            self.assertEqual(audit['conflictDates'],[])
            self.assertEqual(audit['approvedHistoryOnlyDates'],dates)
            self.assertEqual(request['protectedReferenceSessions'],dates)
            self.assertEqual(digest(admission),original_hash)
            for field,value in [('dataset','TICK'),('teacherDatesAdded',1),('originalLedgerRewrite',True)]:
                bad=write_json(Path(tmp)/(field+'.json'),{**approval,field:value})
                with self.assertRaisesRegex(PreopenError,'INVALID_DAILY_HISTORY_EXCEPTION'):
                    enforce_reference_admission({**request,'historyReferenceException':bad},admission)
            with self.assertRaisesRegex(PreopenError,'PROTECTED_REFERENCE_CONFLICT'):
                enforce_reference_admission({**request,'exchangeSessions':['2024-09-09']+request['exchangeSessions'],
                    'protectedReferenceSessions':['2024-09-09']+dates},admission)


if __name__=='__main__':unittest.main()
