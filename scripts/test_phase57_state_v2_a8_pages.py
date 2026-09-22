"""Offline format/failure regression tests; fixtures are synthetic, not raw data."""
import hashlib
import json
import unittest
from phase57_state_v2_a8_pages import decode_pages, RawPageError

D = '2025-06-03'
def row(**extra):
    return {'Date':D,'Code':'330A0','O':100.0,'H':102.0,'L':99.0,'C':101.0,
            'Vo':1000,'Va':100500,'AdjFactor':1.0,'AdjO':50.0,**extra}
def encode(rows):
    text=json.dumps({'data':rows},ensure_ascii=False,separators=(',',':'))
    return {'responseText':text,'responseSha256':hashlib.sha256(text.encode()).hexdigest()}
def data(rows): return json.dumps([encode(rows)]).encode()

class PagesTest(unittest.TestCase):
    def test_response_text_regression(self):
        raw=data([row()]); r,p=decode_pages(raw,D,'daily',hashlib.sha256(raw).hexdigest())
        self.assertEqual(r,[row()]); self.assertEqual(p['responseRowN'],1)
        self.assertTrue(p['individualResponseHashesVerified']); self.assertFalse(p['receivedAtProven'])
    def test_multiple_pages(self):
        r,p=decode_pages(json.dumps([encode([row()]),encode([row(Code='17580')])]).encode(),D,'daily')
        self.assertEqual(len(r),2);self.assertEqual(p['responsePageN'],2)
    def test_empty_documented_page(self):
        r,p=decode_pages(data([]),D,'daily');self.assertEqual(r,[]);self.assertEqual(p['responsePageN'],1)
    def test_missing_factor_not_invented(self):
        x=row();del x['AdjFactor'];r,_=decode_pages(data([x]),D,'daily');self.assertNotIn('AdjFactor',r[0])
    def test_nulls_not_filtered(self):
        x=row(O=None,C=None,AdjFactor=None);r,_=decode_pages(data([x]),D,'daily');self.assertEqual(r,[x])
    def test_nonunit_factor_preserved(self):
        x=row(AdjFactor=.5);r,_=decode_pages(data([x]),D,'daily');self.assertEqual(r,[x])
    def test_minute_exact_clock(self):
        r,_=decode_pages(data([row(Time='09:00')]),D,'minute');self.assertEqual(r[0]['Time'],'09:00')
    def test_file_hash_rejected(self):
        with self.assertRaisesRegex(RawPageError,'RAW_FILE_SHA256'):decode_pages(data([row()]),D,'daily','0'*64)
    def test_page_hash_rejected(self):
        x=encode([row()]);x['responseText']+=' '
        with self.assertRaisesRegex(RawPageError,'PAGE_SHA256'):decode_pages(json.dumps([x]).encode(),D,'daily')
    def test_decoded_rows_not_silently_empty(self):
        with self.assertRaisesRegex(RawPageError,'MISSING_RESPONSE_TEXT'):decode_pages(json.dumps([row()]).encode(),D,'daily')
    def test_wrong_envelope_rejected(self):
        with self.assertRaises(RawPageError):decode_pages(b'{}',D,'daily')
    def test_no_data_field_rejected(self):
        text='{"error":"synthetic"}';x={'responseText':text,'responseSha256':hashlib.sha256(text.encode()).hexdigest()}
        with self.assertRaisesRegex(RawPageError,'MISSING_DATA'):decode_pages(json.dumps([x]).encode(),D,'daily')
    def test_other_day_rejected(self):
        with self.assertRaisesRegex(RawPageError,'RAW_DATE'):decode_pages(data([row(Date='2025-06-04')]),D,'daily')
    def test_code_not_coerced(self):
        with self.assertRaisesRegex(RawPageError,'RAW_CODE'):decode_pages(data([row(Code=330)]),D,'daily')
    def test_minute_without_time_rejected(self):
        with self.assertRaisesRegex(RawPageError,'RAW_MINUTE'):decode_pages(data([row()]),D,'minute')
    def test_duplicate_inner_key_rejected(self):
        text='{"data":[],"data":[]}';x={'responseText':text,'responseSha256':hashlib.sha256(text.encode()).hexdigest()}
        with self.assertRaisesRegex(RawPageError,'DUPLICATE_JSON'):decode_pages(json.dumps([x]).encode(),D,'daily')
    def test_nonfinite_rejected(self):
        with self.assertRaisesRegex(RawPageError,'NONFINITE'):decode_pages(data([row(O=float('nan'))]),D,'daily')
    def test_missing_ohlc_rejected(self):
        x=row();del x['O']
        with self.assertRaisesRegex(RawPageError,'RAW_OHLC'):decode_pages(data([x]),D,'daily')
    def test_kind_rejected(self):
        with self.assertRaisesRegex(RawPageError,'INVALID_KIND'):decode_pages(data([row()]),D,'anything')

if __name__=='__main__':unittest.main()
