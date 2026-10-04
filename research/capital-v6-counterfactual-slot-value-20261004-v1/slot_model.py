"""Runtime inference only: receives allowlisted features and frozen coefficients."""
import numpy as np
def vector(feature,preprocessing):
 fields=preprocessing['numeric_fields'];raw=[feature['numeric'][k] for k in fields]
 v=np.array([float(x) if x is not None else 0. for x in raw]);missing=np.array([float(x is None) for x in raw])
 scaled=(v-np.array(preprocessing['numeric_mean']))/np.array(preprocessing['numeric_std'])
 cat=[]
 for k in preprocessing['categorical_fields']:
  cat.extend(float(feature['categorical'][k]==z) for z in preprocessing['vocabulary'][k])
 return np.r_[scaled,missing,cat]
def probability(feature,model):
 v=vector(feature,model['preprocessing']);logit=float(v@np.array(model['coef'])+model['intercept'])
 return float(np.exp(-np.logaddexp(0.,-logit)))
