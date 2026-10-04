"""Exact inherited Movement preprocessing/prediction functions; no fits."""
import numpy as np
UNKNOWN="__UNKNOWN__"
CATEGORICAL=['state/current_primary', 'state/activity', 'state/basis', 'state/direction_basis', 'state/fast', 'state/numeric_status', 'path/last3_connected_primary']

def transform(train,test,numeric_fields):
 def numeric(rr):
  a=np.array([[float(r['numeric'][k]) if r['numeric'][k] is not None else np.nan for k in numeric_fields] for r in rr])
  assert not np.isinf(a).any()
  return np.column_stack([np.nan_to_num(a,nan=0),np.isnan(a).astype(float)])
 a=numeric(train);z=numeric(test);mu=a.mean(axis=0);scale=a.std(axis=0);scale[scale==0]=1
 vocab={k:sorted({r['categorical'][k] or UNKNOWN for r in train}|{UNKNOWN}) for k in CATEGORICAL}
 def cat(rr):
  col=[]
  for k in CATEGORICAL:
   vv=[r['categorical'][k] if r['categorical'][k] in vocab[k] else UNKNOWN for r in rr]
   col.extend([[float(v==c) for v in vv] for c in vocab[k]])
  return np.array(col).T
 return np.column_stack([(a-mu)/scale,cat(train)]),np.column_stack([(z-mu)/scale,cat(test)]),{
  'numeric_fields':numeric_fields,'categorical_fields':CATEGORICAL,'numeric_mean':mu.tolist(),
  'numeric_scale':scale.tolist(),'categorical_train_vocab':vocab,'constant_missing':0,
  'missing_indicators':True,'training_only':True}

def predict_saved(rr,artifact):
 prep=artifact['preprocessing'];nn=prep['numeric_fields'];cc=prep['categorical_fields']
 a=np.array([[float(r['numeric'][k]) if r['numeric'][k] is not None else np.nan for k in nn] for r in rr])
 a=np.column_stack([np.nan_to_num(a,nan=0),np.isnan(a).astype(float)])
 a=(a-np.array(prep['numeric_mean']))/np.array(prep['numeric_scale']);col=[]
 for k in cc:
  voc=prep['categorical_train_vocab'][k];vv=[r['categorical'][k] if r['categorical'][k] in voc else UNKNOWN for r in rr]
  col.extend([[float(v==c) for v in vv] for c in voc])
 x=np.column_stack([a,np.array(col).T]);logits=x@np.array(artifact['coef'])+artifact['intercept']
 return np.exp(-np.logaddexp(0,-logits))
