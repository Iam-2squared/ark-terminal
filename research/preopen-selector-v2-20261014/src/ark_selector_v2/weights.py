"""One day-uniform normalization, inherited unchanged by the R0 subset."""
from collections import Counter
import numpy as np
from .exact_math import V2Error


def common_weights(sessions: list[str], known: list[bool]) -> tuple[np.ndarray,float]:
    if len(sessions)!=len(known) or not sessions:
        raise V2Error("INVALID_WEIGHT_POPULATION")
    nd=Counter(sessions)  # All G2 rows, including UNKNOWN outcome rows.
    raw=np.asarray([1/nd[d] for d in sessions],dtype=np.float64)
    mask=np.asarray(known,dtype=bool)
    if not mask.any():
        raise V2Error("NO_KNOWN_TEACHER_SUPPORT")
    c=float(mask.sum()/raw[mask].sum())
    return c*raw,c


def used_columns(x: np.ndarray) -> tuple[tuple[int,...],dict[int,str]]:
    if x.ndim!=2 or x.dtype!=np.float64 or np.isinf(x).any():
        raise V2Error("MATRIX_MUST_BE_FINITE_OR_NAN_FLOAT64")
    used=[]
    removed={}
    for j in range(x.shape[1]):
        known=x[:,j][~np.isnan(x[:,j])]
        if known.size==0:
            removed[j]="ALL_MISSING_IN_FIT"
        elif np.all(known==known[0]):
            removed[j]="CONSTANT_IN_FIT"
        else:
            used.append(j)
    if not used:
        raise V2Error("NO_NONCONSTANT_FIT_COLUMNS")
    return tuple(used),removed


def check_cal_support(cal: np.ndarray, used: tuple[int,...]) -> None:
    if np.isinf(cal).any() or cal.dtype!=np.float64:
        raise V2Error("INVALID_CAL_MATRIX")
    if any(np.isnan(cal[:,j]).all() for j in used):
        raise V2Error("BLOCKED_FEATURE_SUPPORT_SHIFT")
