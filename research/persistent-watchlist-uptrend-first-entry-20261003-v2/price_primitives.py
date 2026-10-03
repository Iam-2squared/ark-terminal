"""Exact AST-extracted existing Ark price primitives; parameterized windows only."""

import math

import numpy as np

from types import SimpleNamespace

EMPTY=np.empty((0,7))

def minutes(day):return list(range(540,690))+list(range(750,900 if day<'2024-11-05' else 925))

def pct(a,b):return 100*(a/b-1) if b and b>0 else None

def describe(a,ref,expected):
 keys=['count','coverage','return','high','low','range','volatility','body','upper','lower','volume','value','vwapDistance','closeLocation','timeHigh','timeLow','trendEfficiency']
 z={k:None for k in keys};z.update(count=len(a),coverage=min(1.,len(a)/max(expected,1)))
 if not len(a) or not ref or ref<=0:return z
 o,h,l,c=a[0,1],max(a[:,2]),min(a[:,3]),a[-1,4];vo=sum(a[:,5]);va=sum(a[:,6]);vw=va/vo if vo>0 else None
 z.update(return_=pct(c,o));z['return']=z.pop('return_')
 z.update(high=pct(h,ref),low=pct(l,ref),range=100*(h-l)/ref,body=100*(c-o)/ref,upper=100*(h-max(o,c))/ref,lower=100*(min(o,c)-l)/ref,volume=math.log1p(vo),value=math.log1p(va),vwapDistance=pct(c,vw),closeLocation=(c-l)/(h-l) if h>l else .5,timeHigh=float(a[np.argmax(a[:,2]),0]),timeLow=float(a[np.argmin(a[:,3]),0]),volatility=float(np.std(np.diff(np.log(a[:,4])))*100) if len(a)>1 else None,trendEfficiency=abs(c-o)/max(abs(a[0,4]-o)+sum(abs(np.diff(a[:,4]))),1e-9))
 return z

def ratio(x, y):
    return float(x / y) if x is not None and y is not None and y > 0 else None

def regular(day, a):
    if not len(a):
        return EMPTY.copy()
    end = 900 if day < '2024-11-05' else 925
    return a[((a[:, 0] >= 540) & (a[:, 0] < 690)) |
             ((a[:, 0] >= 750) & (a[:, 0] < end))]

def phase_start(t):
    return 540 if t <= 690 else 750

def window(a, t, n):
    """Strict contiguous closed bars within this half-session, never imputed."""
    if t - n < phase_start(t):
        return None
    x = a[(a[:, 0] >= t - n) & (a[:, 0] < t)]
    if len(x) != n or not np.array_equal(x[:, 0], np.arange(t - n, t)):
        return None
    return x

def observed_vwap(day, a, t):
    x = a[a[:, 0] < t]
    expected = sum(m < t for m in legacy.minutes(day))
    coverage = len(x) / expected if expected else 0.
    value = ratio(float(x[:, 6].sum()), float(x[:, 5].sum())) if len(x) else None
    return (value if coverage >= .8 else None), coverage

def activity(a, previous, t):
    out = {}
    for n in (1, 3, 5, 10):
        cur, pre, hist = window(a, t, n), window(a, t - n, n), window(previous, t, n)
        # Coverage reports actual observed counts even when strict ratios are null.
        for tag, arr, lo, hi in [('current', a, t-n, t), ('preceding', a, t-2*n, t-n),
                                  ('previousDay', previous, t-n, t)]:
            out[f'{n}/{tag}Rows'] = int(np.sum((arr[:, 0] >= max(phase_start(t), lo)) & (arr[:, 0] < hi)))
        for name, col in [('volume', 5), ('value', 6)]:
            c = float(cur[:, col].sum()) if cur is not None else None
            b = float(pre[:, col].sum()) if pre is not None else None
            h = float(hist[:, col].sum()) if hist is not None else None
            out[f'{n}/{name}'] = c
            out[f'{n}/{name}Acceleration'] = ratio(c, b)
            out[f'{n}/{name}RelativePreviousDay'] = ratio(c, h)
    w = window(a, t, 11)
    for name, col in [('volume', 5), ('value', 6)]:
        out[f'compression/{name}Contraction'] = ratio(float(w[5:10, col].sum()), float(w[:5, col].sum())) if w is not None else None
        out[f'expansion/{name}Expansion'] = ratio(float(w[-1, col]), float(w[5:10, col].mean())) if w is not None else None
        z = window(a, t, 2)
        out[f'wick/{name}Confirmation'] = ratio(float(z[-1, col]), float(z[-2, col])) if z is not None else None
    return out

legacy=SimpleNamespace(minutes=minutes)
