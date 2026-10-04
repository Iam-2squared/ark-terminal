"""Pure slot action. Does not import teacher/Oracle or any future books."""
from features import make
from slot_model import probability
def gate(row,positions,pending,cash,equity,history,batch_size,order_index,table,model):
 occ=len(positions)+len(pending);audit={'pre_decision_occupancy':occ,'p_accept':None,'slot_features':None}
 if occ==3:return False,'MAX_POSITION_CAP',audit
 if occ==0:return True,'SLOT1_NO_MODEL_ACCEPT',audit
 assert occ in (1,2)
 feature=make(row,positions,pending,cash,equity,history,batch_size,order_index,table);p=probability(feature,model);audit.update(p_accept=p,slot_features=feature)
 return (True,'SLOT_VALUE_ACCEPT',audit) if p>=.5 else (False,'SLOT_RESERVE_REJECT',audit)
