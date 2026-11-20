from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import no11_auto_master_sources as m

HEADER='<tr><th>コード</th><th>銘柄名</th><th>市場区分</th><th>業種分類</th><th>決算期</th><th>注意情報等</th></tr>'
def listing(code='72030',segment='プライム',sector='輸送用機器',notice=''):
    return '<table>'+HEADER+f'<tr><td>{code}</td><td>Example</td><td>{segment}</td><td>{sector}</td><td>3月</td><td>{notice}</td></tr></table>'

class Sources(unittest.TestCase):
    def test_current_ordinary_stock(self):
        x=m.parse_company(listing(),'7203.T')
        self.assertTrue(x['eligible']);self.assertEqual(x['segment'],'PRIME')
    def test_class_code_not_collapsed(self):
        self.assertFalse(m.parse_company(listing('72035'),'7203.T')['eligible'])
    def test_foreign_or_fund_market_not_ordinary(self):
        for seg in ['ETF','REIT','プライム（外国株）','TOKYO PRO Market']:
            self.assertFalse(m.parse_company(listing(segment=seg),'7203.T')['eligible'])
    def test_unknown_sector_and_attention_excluded(self):
        self.assertFalse(m.parse_company(listing(sector='その他'),'7203.T')['eligible'])
        self.assertFalse(m.parse_company(listing(notice='整理銘柄'),'7203.T')['eligible'])
    def test_header_change_does_not_approve(self):
        with self.assertRaisesRegex(ValueError,'HEADER_CHANGED'):
            m.parse_company('<html>error</html>','7203.T')
    def test_duplicate_listing_rejected(self):
        with self.assertRaisesRegex(ValueError,'AMBIGUOUS'):
            m.parse_company(listing()+listing(),'7203.T')
    def test_rights_codes_not_invented(self):
        self.assertEqual(m.parse_rights_rows([[['配当落等'],['銘柄コード','名称'],[7203.0,'Example'],['123A','Example']]]),['123A.T','7203.T'])
    def test_rights_empty_bad_format_rejected(self):
        with self.assertRaisesRegex(ValueError,'HEADER_CHANGED'):
            m.parse_rights_rows([[['network error']]])
    def test_invalid_rights_code_rejected(self):
        with self.assertRaisesRegex(ValueError,'CODE_FORMAT'):
            m.parse_rights_rows([[['コード'],['???']]])
    def test_current_weekend_rights_source(self):
        html='<a href="/listing/others/ex-rights/x/20261030.xls">2026年10月30日公表分</a>'
        day,url=m.rights_link(html,'2026-10-30','2026-11-02','2026-11-01')
        self.assertEqual(day,'2026-10-30');self.assertTrue(url.endswith('20261030.xls'))
    def test_stale_rights_not_promoted(self):
        html='<a href="/listing/others/ex-rights/x/20261029.xls">old</a>'
        with self.assertRaisesRegex(ValueError,'STALE'):
            m.rights_link(html,'2026-10-30','2026-11-02','2026-11-01')
    def test_untrusted_source_url_blocked(self):
        for url in ['http://www.jpx.co.jp/listing/others/ex-rights/index.html',
                    'https://www.jpx.co.jp.attacker.test/x',
                    'https://user@www.jpx.co.jp/listing/others/ex-rights/x.xls',
                    'https://www.jpx.co.jp:444/listing/others/ex-rights/x.xls']:
            with self.assertRaises(ValueError):m.source_url(url)

if __name__=='__main__':unittest.main()
