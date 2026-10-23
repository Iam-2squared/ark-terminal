"""Synthetic prefix, tri-state, volume and partition canaries."""
import json
import numpy as np

from scripts import phase57_entry_timing_signals as signals
from scripts import phase57_exit_checkpoints_v1 as cp
from scripts import phase57_profit_target_diagnostic as diag
from scripts.phase57_profit_target_precommit import OUT, canonical, jst, check


def run():
    check(not (OUT/'CAUSALITY_TESTS_SUPPLEMENT.json').exists(),'CANARY_ALREADY_SAVED')
    day='2025-07-22';now=542
    prefix=np.asarray([[540,100,101,99,100,10,1000],
                       [541,100,102,99,101,0,0]],dtype=float)
    suffix=np.asarray([[542,100,110,90,109,999,99999]],dtype=float)
    empty=np.empty((0,7))
    a=signals.detect(day,now,None,prefix,empty,None)
    copied=signals.detect(day,now,None,np.concatenate([prefix,suffix])[:2],empty,None)
    check(a==copied,'SUFFIX_INVARIANCE')
    try:signals.detect(day,now,None,np.concatenate([prefix,suffix]),empty,None)
    except AssertionError:pass
    else:raise AssertionError('FUTURE_BAR_ACCEPTED')
    check(all(v['trigger'] in (True,False,None) for v in a['signals'].values()),
          'SIGNAL_TRI_STATE')
    check(a['activity']['1/volume']==0 and a['activity']['1/volumeAcceleration']==0,
          'ZERO_VOLUME_NOT_IGNORED')
    one=np.asarray([prefix[0]],dtype=float)
    b=signals.detect(day,now,None,one,empty,None)
    check(b['activity']['1/volume'] is None,'MISSING_VOLUME_NOT_ZERO')
    known=cp.KnownBar(541,100,102,99,101,0,0,543)
    try:cp.validate_prefix(day,now,(known,))
    except ValueError:pass
    else:raise AssertionError('FUTURE_KNOWN_AT_ACCEPTED')
    entry={'entryId':day+'|X|540','session':day,'symbol':'X','entryMinute':540,
           'entryPrice':100.,'entryCostJpy':'10000','futureUpsidePctEvaluatorOnly':5.,
           'ccmgFirstIntentMinute':None,'deltaPnlJpy':None}
    r50={'decisionNow':545,'exitMinute':545,'exitPrice':101.,'exitKind':'MODEL_EXIT'}
    path={int(q[0]):q.tolist() for q in prefix}
    x=diag.market_row('IM',1,entry,r50,path,[],None,False,False)
    entry['futureUpsidePctEvaluatorOnly']=999.
    entry['deltaPnlJpy']='-99999999'
    y=diag.market_row('IM',1,entry,r50,path,[],None,False,False)
    check((x['choice'],x['candidateFillPrice'],x['100'])==
          (y['choice'],y['candidateFillPrice'],y['100']), 'FUTURE_LABEL_CHANGED_CHOICE')
    record={'status':'SYNTHETIC_CAUSALITY_PASS','atJst':jst(),
            'futureSuffixChangesPrefix':False,'unclosedBarRejected':True,
            'knownAtAfterDecisionRejected':True,'futureLabelMutationNoDecisionEffect':True,
            'signalThreeValuesPreserved':True,'realZeroVolumeVsMissingDistinct':True,
            'livePublicationLatencyProven':False,
            'savedStateSignalTargetJoinProven':False}
    (OUT/'CAUSALITY_TESTS_SUPPLEMENT.json').write_bytes(canonical(record))
    print(json.dumps(record))


if __name__=='__main__':run()
