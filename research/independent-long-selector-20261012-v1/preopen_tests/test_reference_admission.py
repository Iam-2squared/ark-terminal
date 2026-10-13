import unittest
from pathlib import Path
import sys
from datetime import date,timedelta

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from preopen_reference_admission import reference_dependencies,enforce_reference_admission
from preopen_selector import PreopenError


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


if __name__=='__main__':unittest.main()
