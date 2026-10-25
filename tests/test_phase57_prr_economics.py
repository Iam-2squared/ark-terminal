"""Synthetic focused cases before archived PRR economic evaluation."""
import unittest
from decimal import Decimal

from scripts.phase57_prr_rank import low, route
from scripts.phase57_prr_economics import metrics, pnl100


def row(**changes):
    r = {"controlPnlJpy": "0", "routedPnlJpy": "0", "ccmgPnlJpy": "0",
         "r54PnlJpy": "0", "routeDecision": "CONTROL_DEFAULT",
         "terminalReason": "R50_CONTROL_DEFAULT", "initialOrReplacement": "Initial"}
    return {**r, **changes}


class FocusedEconomics(unittest.TestCase):
    pass


LOW_CASES = [
    ("negative", -1., 0., True), ("equal_zero", 0., 0., False),
    ("positive", 1., 0., False), ("negative_median", -2., -1., True),
    ("equal_negative", -1., -1., False), ("above_negative", 0., -1., False),
    ("strict_ulps", -.0000001, 0., True), ("same_fraction", .5, .5, False),
]
for name, score, median, expected in LOW_CASES:
    def check(self, score=score, median=median, expected=expected):
        self.assertIs(low(score, median), expected)
    setattr(FocusedEconomics, "test_low_" + name, check)

ROUTE_CASES = [
    ("both_low", True, True, "DEFENSIVE_ELIGIBLE"),
    ("low5_only", True, False, "CONTROL_DEFAULT"),
    ("low10_only", False, True, "CONTROL_DEFAULT"),
    ("neither_low", False, False, "CONTROL_DEFAULT"),
]
for name, five, ten, expected in ROUTE_CASES:
    def check(self, five=five, ten=ten, expected=expected):
        self.assertEqual(route(five, ten), expected)
    setattr(FocusedEconomics, "test_route_" + name, check)

PNL_CASES = [
    ("null_exit", "100", None, None),
    ("flat_sell_fee", "100", "100", "-5.00000"),
    ("profit", "100", "110", "994.50000"),
    ("loss", "100", "90", "-1004.50000"),
    ("fractional", "123.45", "123.46", "-5.173000"),
]
for name, entry, exit_price, expected in PNL_CASES:
    def check(self, entry=entry, exit_price=exit_price, expected=expected):
        actual = pnl100(entry, exit_price)
        if expected is None:
            self.assertIsNone(actual)
        else:
            self.assertEqual(Decimal(actual), Decimal(expected))
    setattr(FocusedEconomics, "test_pnl100_" + name, check)


def assert_metric(test, actual, field, expected):
    if isinstance(expected, str) and field.endswith("Jpy"):
        test.assertEqual(Decimal(actual[field]), Decimal(expected))
    else:
        test.assertEqual(actual[field], expected)


METRIC_CASES = [
    ("default_equality", [row()], "pairedDeltaJpy", "0"),
    ("improvement", [row(controlPnlJpy="1", routedPnlJpy="2")],
     "pairedDeltaJpy", "1"),
    ("regression", [row(controlPnlJpy="2", routedPnlJpy="1")],
     "pairedDeltaJpy", "-1"),
    ("null_not_zero", [row(routedPnlJpy=None)], "knownPairedN", 0),
    ("null_coverage", [row(), row(routedPnlJpy=None)], "knownCoverage", .5),
    ("defensive_count", [row(routeDecision="DEFENSIVE_ELIGIBLE")],
     "defensiveRouteN", 1),
    ("candidate_first", [row(routeDecision="DEFENSIVE_ELIGIBLE",
                              terminalReason="CANDIDATE_FIRST")],
     "candidateFirstSellN", 1),
    ("exact_decimal", [row(controlPnlJpy="0.1", routedPnlJpy="0.3")],
     "pairedDeltaJpy", "0.2"),
]
for name, fixture, field, expected in METRIC_CASES:
    def check(self, fixture=fixture, field=field, expected=expected):
        assert_metric(self, metrics(fixture), field, expected)
    setattr(FocusedEconomics, "test_metric_" + name, check)


if __name__ == "__main__":
    unittest.main()
