"""Audit-only event ordering edges; no dataset replay."""
import unittest
from independent_audit import decision_overlaps_position

class EventOrder(unittest.TestCase):
    def test_just_sealed_fresh_cross_precedes_next_open_same_timestamp(self):
        self.assertFalse(decision_overlaps_position(603,1,[{'trade_index':2,'buy_minute':603,'sell_minute':700}]))
    def test_next_closed_decision_while_position_open_rejected(self):
        self.assertTrue(decision_overlaps_position(604,1,[{'trade_index':2,'buy_minute':603,'sell_minute':700}]))
    def test_already_existing_same_timestamp_position_is_not_exempt(self):
        self.assertTrue(decision_overlaps_position(603,2,[{'trade_index':2,'buy_minute':603,'sell_minute':700}]))
    def test_sell_fill_minute_remains_inclusive_for_old_position(self):
        self.assertTrue(decision_overlaps_position(700,2,[{'trade_index':2,'buy_minute':603,'sell_minute':700}]))
    def test_after_fill_flat(self):
        self.assertFalse(decision_overlaps_position(701,2,[{'trade_index':2,'buy_minute':603,'sell_minute':700}]))
    def test_unresolved_position_never_flat(self):
        self.assertTrue(decision_overlaps_position(800,2,[{'trade_index':2,'buy_minute':603,'sell_minute':None}]))

if __name__=='__main__':unittest.main()
