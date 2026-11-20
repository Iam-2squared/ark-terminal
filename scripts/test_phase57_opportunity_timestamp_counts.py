import unittest
from scripts.phase57_opportunity_timestamp_counts import events_from_decisions,build

def sample():
 base={'anchorId':'anchor','symbol':'12340','session':'2024-09-17','decisionTimestamp':'2024-09-17T09:30:00+09:00'}
 return {'sessionDate':'2024-09-17','decision':{'initialEvent':{**base,'eventType':'INITIAL_ENTRY_OPPORTUNITY','opportunityTimestamp':base['decisionTimestamp'],'referenceStatus':'UNKNOWN_REFERENCE_OPEN'},'secondaryEvent':{**base,'eventType':'DIP_REPRICE_OPPORTUNITY','opportunityTimestamp':'2024-09-17T09:35:00+09:00','referenceStatus':'REFERENCE_OPEN'}}}
class OpportunityCounts(unittest.TestCase):
 def test_dip_emission_timestamp_not_anchor(self):
  es=events_from_decisions([sample()]);self.assertEqual([e['timestamp'][11:16] for e in es],['09:30','09:35'])
 def test_missing_reference_still_emitted(self):
  es=events_from_decisions([sample()]);self.assertEqual(len(es),2);self.assertEqual(es[0]['referenceStatus'],'UNKNOWN_REFERENCE_OPEN')
 def test_duplicate_opportunity_rejected(self):
  with self.assertRaises(AssertionError):events_from_decisions([sample(),sample()])
 def test_saved_ledger_conservation_and_calendar(self):
  rows,s=build();self.assertEqual(sum(r['opportunityEvents'] for r in rows),3508)
  self.assertEqual(s['audits']['symbolTimestampDuplicateEvents'],0)
  self.assertTrue(all(not '11:35'<=r['timestamp'][11:16]<'12:30' for r in rows))
  self.assertEqual(sum(v['timestamps'] for v in s['panels']['ALL_TRADING_5M_GRID_WITH_BOUNDARIES']['distribution'].values()),len(rows))
if __name__=='__main__':unittest.main()
