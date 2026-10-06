"""Native old preprocessing semantics with shape support for empty families."""
import numpy as np
from sign_io import *

def transform(train, test, nn, cc, prep=None):
    def nums(rr):
        a=np.array([[float(r['numeric'][k]) if r['numeric'][k] is not None else np.nan for k in nn] for r in rr],dtype=float).reshape(len(rr),len(nn))
        assert not np.isinf(a).any()
        return np.column_stack([np.nan_to_num(a,nan=0),np.isnan(a).astype(float)])
    if prep is None:
        a=nums(train); mu=a.mean(axis=0); scale=a.std(axis=0); scale[scale==0]=1
        prep={'numeric_fields':nn,'categorical_fields':cc,'numeric_mean':mu.tolist(),'numeric_scale':scale.tolist(),
              'categorical_train_vocab':{k:sorted({r['categorical'][k] or '__UNKNOWN__' for r in train}|{'__UNKNOWN__'}) for k in cc},
              'missing_constant':0,'missing_indicators':True,'train_only':True}
    def apply(rr):
        a=(nums(rr)-np.array(prep['numeric_mean']))/np.array(prep['numeric_scale']); columns=[]
        for k in cc:
            voc=prep['categorical_train_vocab'][k]
            values=[r['categorical'][k] if r['categorical'][k] in voc else '__UNKNOWN__' for r in rr]
            columns.extend([[float(v==c) for v in values] for c in voc])
        cats=np.array(columns,dtype=float).T if columns else np.empty((len(rr),0))
        return np.column_stack([a,cats])
    return apply(train) if train else None,apply(test),prep
