"""Exactly one bounded scalar optimizer per estimator, no estimator fit."""
from dataclasses import dataclass
from typing import Callable, Any
import numpy as np
from scipy.special import logsumexp
from scipy.optimize import minimize_scalar
from .exact_math import V2Error


def probability_matrix(p: Any, classes: int) -> np.ndarray:
    p=np.asarray(p,dtype=np.float64)
    if p.ndim!=2 or p.shape[1]!=classes or not np.isfinite(p).all() or np.any((p<0)|(p>1)):
        raise V2Error("INVALID_PROBABILITY_VECTOR")
    if np.any(np.abs(p.sum(axis=1)-1)>1e-12):
        raise V2Error("PROBABILITY_SUM_MISMATCH")
    return p


def temperature(p: np.ndarray, beta: float) -> np.ndarray:
    p=probability_matrix(p,p.shape[1])
    if not np.isfinite(beta) or beta<=0:
        raise V2Error("INVALID_INVERSE_TEMPERATURE")
    z=np.log(np.maximum(p,1e-15))*beta
    return np.exp(z-logsumexp(z,axis=1,keepdims=True))


@dataclass(frozen=True)
class Temperature:
    beta: float
    objective_calls: int
    iterations: int
    nll_before: float
    nll_after: float
    convergence: str


def fit_temperature(p: np.ndarray, y: np.ndarray, weights: np.ndarray,
                    *, optimizer: Callable[...,Any] = minimize_scalar) -> Temperature:
    p=probability_matrix(p,p.shape[1])
    if len(y)!=len(p) or len(weights)!=len(p) or len(p)==0 or not np.isfinite(weights).all() or np.any(weights<=0):
        raise V2Error("INVALID_CALIBRATION_TEACHERS_OR_WEIGHTS")
    if y.dtype.kind not in "iu" or np.any((y<0)|(y>=p.shape[1])):
        raise V2Error("INVALID_CALIBRATION_CLASS_ORDER")
    logits=np.log(np.maximum(p,1e-15))
    calls=0
    def loss(beta: float) -> float:
        nonlocal calls
        calls+=1
        z=beta*logits
        value=float(np.average(logsumexp(z,axis=1)-z[np.arange(len(y)),y],weights=weights))
        if not np.isfinite(value):
            raise V2Error("CALIBRATION_REVIEW_REQUIRED_NONFINITE")
        return value
    probes=[loss(b) for b in (0.05,1,20)]
    if max(probes)-min(probes)<=1e-12:
        raise V2Error("CALIBRATION_REVIEW_REQUIRED_FLAT")
    result=optimizer(loss,bounds=(0.05,20),method="bounded",options={"maxiter":200,"xatol":1e-8})
    beta=float(result.x)
    if (not result.success or not np.isfinite(beta) or not np.isfinite(result.fun)
            or beta<=0.05+1e-6 or beta>=20-1e-6):
        raise V2Error("CALIBRATION_REVIEW_REQUIRED_BOUND_OR_NONCONVERGENCE")
    return Temperature(beta,calls,int(result.nfev),probes[1],float(result.fun),"CONVERGED_INTERIOR")
