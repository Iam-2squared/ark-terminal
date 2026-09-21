"""Audit saved census evidence without replaying or training any project model."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import phase57_entry_timing_census as c


def verify():
    p=c.s.verify();base=c.s.BASE
    for folder in ('measurement','report'):
        root=base/folder
        for name,digest in c.read(root/'manifest.json').items():
            assert c.sha(root/name)==digest,(folder,name)
    root=base/'measurement';ids=set(p['opportunityIds'])
    records=c.read(root/'opportunity-records.json.gz')
    assert len(records)==len(ids)==2155
    assert {r['opportunity'] for r in records}==ids
    trades=c.read(root/'trades.json.gz');paired=c.read(root/'paired.json.gz')
    for arm in c.ARMS:
        assert len(trades[arm])==len(paired[arm])==2155
        assert {r['opportunity'] for r in trades[arm]}==ids
        assert all(r['modelRejection'] is False for r in trades[arm])
        for r in trades[arm]:
            if not r['entryId'] and r['unfilledReason']!='SESSION_BOUNDARY':
                assert r['buyAttemptCount']>0
    metrics=c.read(root/'metrics.json')
    assert metrics['A']['fills']==1963
    anatomy=c.read(root/'oracle-anatomy.json')
    assert anatomy['selectorBelow1']==596 and anatomy['unknownFullSession']==63
    assert [anatomy['thresholds'][str(k)]['orderedLowLaterHigh'] for k in [1,2,3,4,5,10]]==[1895,1504,1143,854,666,229]
    co=c.read(root/'cohort.json')
    assert co['holdoutOpened']==0 and co['noTraining'] and co['noDictionary']
    assert all(v is False for v in co['safety'].values())
    validation=c.read(base/'validation/completion-ci.json')
    assert c.sha(base/'validation/completion.json') == validation['originalCompletionSHA256']
    assert validation['fullCensusRegenerationIdentical']
    assert validation['correctedEvaluationRegenerationIdentical']
    assert validation['reportRegenerationIdentical']
    assert validation['regressionPassed']==2949
    for name,digest in validation['implementationPins'].items():
        assert c.sha(c.s.ROOT/name)==digest,name
    print('ENTRY_TIMING_SIGNAL_CENSUS_V1_INTEGRITY_PASS | 2155 fixed | no training/promotion')


if __name__=='__main__':
    verify()
