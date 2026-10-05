"""Pure certificates and evaluation contracts; no market loop or state transition."""
from fractions import Fraction
import hashlib

def prefix_certificate(initial_equal,transitions_equal,state_complete,exception_quantities):
    if not state_complete:return 'UNMEASURABLE'
    if any(q>=100 for q in exception_quantities):return 'FIRST_DIVERGENCE_FOUND'
    if initial_equal and all(transitions_equal):return 'NO_EFFECT_PROVEN'
    return 'PREFIX_IDENTITY_UNPROVEN'

def accept_saved_prefix(divergence_found):
    if divergence_found:raise ValueError('SAVED_V5_STATE_AFTER_FIRST_DIVERGENCE_FORBIDDEN')
    return True

def settlement_contract(buy_committed,source_complete):
    if buy_committed and not source_complete:
        return {'status':'EXECUTION_MEASUREMENT_BLOCKED','buy_retained':True,'unresolved_obligation':True}
    return {'status':'COMPLETE' if buy_committed else 'NOT_EXECUTED','buy_retained':buy_committed,'unresolved_obligation':False}

def exact_E1(v5,r):
    assert len(v5)==len(r)==19
    return all(Fraction(a)<=Fraction(b) for a,b in zip(v5,r))

def exact_Q3(nonpositive,total,positive):
    return total>0 and nonpositive<82 and nonpositive*150<82*total and positive>=68

def verify_frozen_bytes(payload,expected_sha256):
    if hashlib.sha256(payload).hexdigest()!=expected_sha256:raise ValueError('FROZEN_INPUT_CHANGED_STOP')
    return True
