import copy
import unittest
from datetime import timedelta
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from preopen_selector import PreopenError, stamp
from preopen_compact_source import tick_features_for_group, reconciled_totals
from preopen_history_features import prior_tick_features
from preopen_source_contracts import official_security_class, native_available_at, converted_native_value
from preopen_native_source import minute_row


class CompactTickParity(unittest.TestCase):
    def rows(self):
        clocks = ['09:00:00.000000','11:30:00.000000','12:30:00.000000',
                  '13:30:00.000000','14:29:00.000000','14:31:00.000000',
                  '14:31:00.000000','14:59:00.000000','15:24:00.000000','15:30:00.000000']
        return [dict(Date='2024-11-13',Code='13010',Time=t,Price=str(100+i),
                     TradingVolume=str(100+100*i),TransactionId=f'{i+1:012d}')
                for i,t in enumerate(clocks)]

    def test_bounded_window_matches_whole_stream_and_retains_same_time_records(self):
        rows=self.rows();cutoff='2024-11-13T16:30:00+09:00'
        reduced,totals,n=tick_features_for_group(rows,previous_session='2024-11-13',
            cutoff=cutoff,reference_price='109')
        whole=prior_tick_features([dict(tradeAt=r['Date']+'T'+r['Time']+'+09:00',
            availableAt=cutoff,price=r['Price'],quantity=r['TradingVolume']) for r in rows],
            previous_session='2024-11-13',cutoff=cutoff,reference_price='109',complete_source_verified=True)
        self.assertEqual(reduced,whole)
        self.assertEqual(totals['rows'],10)
        self.assertLess(n,len(rows))
        self.assertEqual(reduced['preopen_previous_tick_tick_trade_count_60m'],5)

    def test_saved_daily_reconciliation_does_not_certify_missing_or_duplicated_volume(self):
        _,totals,_=tick_features_for_group(self.rows(),previous_session='2024-11-13',
            cutoff='2024-11-13T16:30:00+09:00',reference_price='109')
        raw=dict(zip(('O','H','L','C','Vo','Va'),
                     (totals[k] for k in ('open','high','low','close','volume','turnover'))))
        self.assertTrue(reconciled_totals(totals,raw))
        raw['Vo']=str(int(raw['Vo'])+100)
        self.assertFalse(reconciled_totals(totals,raw))

    def test_transaction_conflict_and_lunch_price_are_errors(self):
        rows=self.rows();rows[6]['TransactionId']=rows[5]['TransactionId']
        with self.assertRaisesRegex(PreopenError,'TRANSACTION'):
            tick_features_for_group(rows,previous_session='2024-11-13',
                cutoff='2024-11-13T16:30:00+09:00',reference_price=109)
        rows=self.rows();rows[2]['Time']='12:00:00.000000'
        with self.assertRaisesRegex(PreopenError,'DATED_SESSION'):
            tick_features_for_group(rows,previous_session='2024-11-13',
                cutoff='2024-11-13T16:30:00+09:00',reference_price=109)

    def test_no_recent_tape_preserves_age_without_fabricated_recent_returns(self):
        rows=self.rows()[:2];cutoff='2024-11-13T16:30:00+09:00'
        f,_,_=tick_features_for_group(rows,previous_session='2024-11-13',cutoff=cutoff,reference_price=101)
        self.assertGreater(f['preopen_previous_tick_tick_last_trade_age_seconds'],3600)
        self.assertIsNone(f['preopen_previous_tick_tick_vwap_distance_60m_pct'])


class NativeFieldEvidence(unittest.TestCase):
    def test_product_market_and_date_prevent_suffix_only_classification(self):
        base=dict(Date='2024-10-02',Code='186A0',Mkt='0113',ProdCat='011')
        self.assertTrue(official_security_class(base,session=base['Date'])['commonStock'])
        for change in ({'ProdCat':'014'},{'Mkt':'0101'},{'Code':'186A1'},
                       {'Code':'83010'},{'Code':'84210'}):
            self.assertFalse(official_security_class({**base,**change},session=base['Date'])['commonStock'])
        with self.assertRaisesRegex(PreopenError,'DATED_MASTER'):
            official_security_class(base,session='2024-10-03')
        with self.assertRaisesRegex(PreopenError,'MISSING_PRODUCT'):
            official_security_class({**base,'ProdCat':''},session=base['Date'])

    def test_calendar_publication_and_units_do_not_mix_date_and_timestamp(self):
        src=dict(dataset='INVESTOR_TYPES',dateField='PubDate',availabilityContract={
            'evidenceReference':'OFFICIAL_SCHEDULE_ASSUMPTION','publicationTime':'16:30:00',
            'dateRule':'NEXT_EXCHANGE_SESSION'})
        self.assertEqual(native_available_at({'PubDate':'2024-11-01'},src,
            calendar=['2024-11-01','2024-11-05']),'2024-11-05T16:30:00+09:00')
        self.assertEqual(converted_native_value('123.45','MILLION_JPY',output_unit='JPY'),(123450000.,'JPY'))
        self.assertEqual(converted_native_value('0.231','RATIO',output_unit='PERCENT'),(23.1,'PERCENT'))
        with self.assertRaisesRegex(PreopenError,'CONVERSION'):
            converted_native_value('1','SHARES',output_unit='JPY')

    def test_terminal_auction_bucket_is_not_available_at_its_start(self):
        raw=dict(Date='2024-11-13',Time='15:30',Code='13010',O='100',H='100',L='100',C='100',Vo='100',Va='10000')
        bar=minute_row(raw,'2024-11-13T16:30:00+09:00')
        self.assertEqual(stamp(bar['end'])-stamp(bar['start']),timedelta(minutes=1))
        with self.assertRaisesRegex(PreopenError,'BEFORE_COMPLETE'):
            minute_row(raw,'2024-11-13T15:30:00+09:00')


if __name__=='__main__':unittest.main()
