from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import no11_weekly_security_policy as p
import no11_jpx_weekly_sources as source
import no11_operations_profile as profile

NOW = '2026-11-09T09:10:00.000+09:00'
SYMS = ['7203.T', '6758.T']


def fixture():
    weekly = p.make_weekly(week_start='2026-11-09', known_at='2026-11-06T18:00:00+09:00',
        metadata_asof='2026-09-30', source_sha256='a' * 64,
        rows=[{'symbol': s, 'commonEquity': True, 'segment': 'PRIME', 'sector': 'synthetic'} for s in SYMS])
    reference = {'schemaId': 'ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1',
        'sessionDate': '2026-11-09', 'source': 'RssMarket_SELECTED_REFERENCE_READONLY',
        'readOnly': True, 'orderTransmission': False, 'productionReady': False,
        'selectedSymbols': SYMS[:], 'chartPlanSha256': 'b' * 64,
        'capturedAtJst': '2026-11-09T09:09:55.000+09:00',
        'completedAtJst': '2026-11-09T09:09:58.000+09:00',
        'rows': [{'symbol': s, 'marketCode': 'T', 'marketDate': '2026-11-09',
            'previousDate': '2026-11-06', 'marketSection': '東証Ｐ', 'lotShares': 100,
            'previousClose': 1000.0, 'dayBasePrice': 1000.0,
            'exRightsDateRaw': '', 'exDividendDateRaw': '2027/03/29',
            'interimExDividendDateRaw': ''} for s in SYMS]}
    changes = {'schemaId': p.CHANGES, 'sessionDate': '2026-11-09',
        'observedAtJst': '2026-11-09T09:09:00.000+09:00', 'readOnly': True,
        'orderTransmission': False, 'blocked': [],
        'coverage': {k: {'status': 'PARSED', 'sourceSha256': 'c' * 64,
                        'sourceUrl': source.SOURCES[k][0]} for k in p.REQUIRED_FEEDS}}
    return weekly, reference, changes


def admit(w=None, r=None, c=None):
    defaults = fixture()
    w = defaults[0] if w is None else w
    r = defaults[1] if r is None else r
    c = defaults[2] if c is None else c
    return p.admit(weekly=w, reference=r, changes=c, session='2026-11-09',
        previous_session='2026-11-06', now=NOW, selected=SYMS[:], protected=['9432.T'])


class WeeklyPolicy(unittest.TestCase):
    def test_actual_session_view_keeps_weekly_metadata(self):
        result, master = admit()
        self.assertEqual(result['admittedEntrySymbols'], SYMS)
        self.assertFalse(result['scopeMustBeRebuiltBeforeRuntime'])
        self.assertEqual(master['corporateActionReviewSource'], p.BASIS)
        self.assertFalse(master['independentHumanSameDayReviewPerformed'])
        self.assertFalse(master['orderTransmission'])
        self.assertEqual(master['rows'][0]['asOfSession'], '2026-11-09')

    def test_one_invalid_security_does_not_block_others_or_exit(self):
        w, r, c = fixture()
        c['blocked'] = [{'symbol': SYMS[0], 'kind': 'supervision'}]
        result, master = admit(w, r, c)
        self.assertEqual(result['admittedEntrySymbols'], [SYMS[1]])
        self.assertEqual(result['protectedExitSymbols'], ['9432.T'])
        self.assertTrue(result['scopeMustBeRebuiltBeforeRuntime'])
        self.assertEqual(len(master['rows']), 1)

    def test_price_adjustment_never_inferred_away(self):
        w, r, c = fixture()
        r['rows'][0]['dayBasePrice'] = 500.0
        result, _ = admit(w, r, c)
        self.assertIn('PRICE_BASIS_DIFFERENCE', result['excludedEntrySymbols'][SYMS[0]])

    def test_current_ex_date_is_excluded(self):
        w, r, c = fixture()
        r['rows'][1]['exRightsDateRaw'] = '2026/11/09'
        result, _ = admit(w, r, c)
        self.assertIn('CURRENT_EX_DATE', result['excludedEntrySymbols'][SYMS[1]])

    def test_missing_action_field_not_cleared(self):
        w, r, c = fixture()
        del r['rows'][1]['exRightsDateRaw']
        result, _ = admit(w, r, c)
        self.assertIn('ACTION_FIELD_MISSING', result['excludedEntrySymbols'][SYMS[1]])

    def test_future_monthly_source_rejected(self):
        with self.assertRaisesRegex(ValueError, 'METADATA_STALE_OR_FUTURE'):
            p.make_weekly(week_start='2026-11-09', known_at='2026-11-06T18:00:00+09:00',
                metadata_asof='2026-11-30', source_sha256='f' * 64, rows=[])

    def test_prior_week_cannot_be_redated(self):
        w, r, c = fixture()
        old = p.make_weekly(week_start='2026-11-02', known_at='2026-10-30T18:00:00+09:00',
            metadata_asof='2026-09-30', source_sha256='f' * 64, rows=w['rows'])
        with self.assertRaisesRegex(ValueError, 'WRONG_OR_EXPIRED_WEEK'):
            admit(old, r, c)

    def test_modified_weekly_cache_rejected(self):
        w, r, c = fixture()
        w['rows'][0]['sector'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'WEEKLY_HASH'):
            admit(w, r, c)

    def test_unavailable_change_source_not_empty_success(self):
        w, r, c = fixture()
        c['coverage']['rights']['status'] = 'UNAVAILABLE'
        with self.assertRaisesRegex(ValueError, 'CHANGE_FEED_UNAVAILABLE_RIGHTS'):
            admit(w, r, c)

    def test_stale_change_feed_rejected(self):
        w, r, c = fixture()
        c['observedAtJst'] = '2026-11-09T09:00:00+09:00'
        with self.assertRaisesRegex(ValueError, 'SESSION_CHANGES_STALE'):
            admit(w, r, c)

    def test_stale_quote_and_future_quote_rejected(self):
        for time in ('2026-11-09T09:00:00+09:00', '2026-11-09T09:11:00+09:00'):
            w, r, c = fixture()
            r['capturedAtJst'] = r['completedAtJst'] = time
            with self.assertRaisesRegex(ValueError, 'REFERENCE_STALE_OR_CLOCK'):
                admit(w, r, c)

    def test_unknown_or_wrong_market_excluded(self):
        w, r, c = fixture()
        r['rows'][0]['marketSection'] = 'ETF'
        r['rows'][1]['lotShares'] = 1
        result, master = admit(w, r, c)
        self.assertFalse(result['newBuyAllowed'])
        self.assertEqual(master['rows'], [])
        self.assertEqual(result['protectedExitSymbols'], ['9432.T'])

    def test_date_parser(self):
        self.assertEqual(p.action_date('2026/11/09').isoformat(), '2026-11-09')
        self.assertIsNone(p.action_date(''))
        with self.assertRaises(ValueError):
            p.action_date('not observed')


class PublicSources(unittest.TestCase):
    def test_parse_recognized_code_table(self):
        raw = '<h1>監理銘柄</h1><table><tr><th>指定日</th><th>コード</th><th>銘柄</th></tr><tr><td>2026/11/01</td><td>7203</td><td>synthetic</td></tr></table>'.encode()
        self.assertEqual(source.parse_exceptions('supervision', raw), ['7203.T'])

    def test_unknown_page_is_not_empty_success(self):
        with self.assertRaises(ValueError):
            source.parse_exceptions('supervision', b'<html>unavailable</html>')

    def test_malformed_code_rejected(self):
        raw = '<h1>監理</h1><table><tr><th>コード</th></tr><tr><td>missing</td></tr></table>'.encode()
        with self.assertRaises(ValueError):
            source.parse_exceptions('supervision', raw)

    def test_explicit_no_issues(self):
        raw = '<h1>売買停止</h1><p>該当する銘柄はありません</p>'.encode()
        self.assertEqual(source.parse_exceptions('suspension', raw), [])

    def test_private_or_redirect_host_rejected(self):
        for url in ('http://www.jpx.co.jp/a', 'https://example.com/a',
                    'https://user:pass@www.jpx.co.jp/a'):
            with self.assertRaises(ValueError):
                source.origin(url)

    def test_weekly_cache_only_downloads_once(self):
        w, _, _ = fixture()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            with patch.object(source, 'parse_workbook', return_value=('2026-09-30', w['rows'])):
                calls = []
                def download(url):
                    calls.append(url)
                    return b'PUBLIC_FIXTURE_ONLY'
                a = source.refresh_weekly(root, '2026-11-09', '2026-11-06T18:00:00+09:00', download)
                b = source.refresh_weekly(root, '2026-11-09', NOW, download)
                self.assertEqual(a, b)
                self.assertEqual(len(calls), 1)


class OperationProfile(unittest.TestCase):
    def test_default_cash_general_sor_market(self):
        value = profile.validate(deepcopy(profile.POLICY))
        self.assertTrue(value['sor'])
        self.assertEqual(value['accountType'], 1)
        self.assertEqual(value['account'], '一般')
        self.assertFalse(value['orderTransmission'])
        self.assertFalse(value['autoAdoptExternalHoldings'])

    def test_staged_broker_never_inherits_permissions(self):
        template = {'schemaId': 'ARK_NO11_BROKER_EXECUTION_CONFIG_V1',
            'ledger': {'maxSymbols': 3, 'lotSize': 100}, 'orderTransmission': False,
            'transport': {'mode': 'DISABLED'}}
        c = profile.stage_broker_configuration(template, profile.POLICY)
        self.assertTrue(c['orderTerms']['sor'])
        self.assertEqual(c['transport'], {'mode': 'DISABLED', 'orderTransmission': False})
        self.assertNotIn('orderTerms', template)
        template['orderTransmission'] = True
        with self.assertRaises(ValueError):
            profile.stage_broker_configuration(template, profile.POLICY)

    def test_large_or_missing_per_order_limit_rejected(self):
        v = {'schemaId': 'ARK_NO11_BROKER_UI_SETUP_DECLARATION_V1',
            'bankLink': 'NONE', 'autoSweepEnabled': False, 'rssOrderFeatureConfigured': True,
            'orderConfirmationDialogDisabled': True, 'tradingWarningDialogDisabled': True,
            'rssPerOrderLimitJpy': 1000000000, 'operatorBudgetCeilingJpy': 1000000,
            'marginNewOrderLimitJpy': 0}
        with self.assertRaises(ValueError):
            profile.validate_setup_declaration(v, profile.POLICY)
        v['rssPerOrderLimitJpy'] = 100000
        self.assertFalse(profile.validate_setup_declaration(v, profile.POLICY)['orderTransmission'])

    def test_newer_blocked_cannot_fallback_to_old_success(self):
        ok = {'schemaId': 'ARK_NO11_ACCOUNT_OBSERVATION_ENVELOPE_V1', 'status': 'OBSERVED',
            'runId': 'synthetic', 'sequence': 1, 'readOnly': True, 'orderTransmission': False,
            'brokerObservation': {'status': 'OBSERVED', 'captureCompletedAt': '2026-11-09T09:09:59+09:00'}}
        self.assertEqual(profile.select_current_observation([ok], NOW)['sequence'], 1)
        bad = dict(ok, sequence=2, status='BLOCKED')
        with self.assertRaisesRegex(ValueError, 'LATEST_OBSERVATION_BLOCKED'):
            profile.select_current_observation([ok, bad], NOW)

    def test_external_manual_holding_not_adopted(self):
        snapshot = {'status': 'OBSERVED', 'positions': [{'symbol': '7203'}, {'symbol': '6758.T'}]}
        self.assertEqual(profile.external_symbols(snapshot, ['6758.T']), ['7203.T'])


if __name__ == '__main__':
    unittest.main()
