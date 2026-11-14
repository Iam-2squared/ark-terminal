"""Integer coefficient/exponent arithmetic. No Decimal arithmetic or shared parser."""
import re
from decimal import Decimal
from math import gcd
TOKEN=re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?',re.ASCII)
class N:
    __slots__=('c','e')
    def __init__(self,c=0,e=0):
        if isinstance(c,N): self.c,self.e=c.c,c.e;return
        if isinstance(c,str):
            q=parse(c);self.c,self.e=q.c,q.e;return
        while c and c%10==0:c//=10;e+=1
        self.c,self.e=(c,e) if c else (0,0)
    def __deepcopy__(self,memo):return self
    def is_finite(self):return True
    def align(self,v):
        v=N(v);e=min(self.e,v.e);return self.c*10**(self.e-e),v.c*10**(v.e-e),e
    def __add__(self,v):a,b,e=self.align(v);return N(a+b,e)
    __radd__=__add__
    def __neg__(self):return N(-self.c,self.e)
    def __sub__(self,v):return self+-N(v)
    def __rsub__(self,v):return N(v)+-self
    def __mul__(self,v):v=N(v);return N(self.c*v.c,self.e+v.e)
    __rmul__=__mul__
    def __abs__(self):return N(abs(self.c),self.e)
    def __bool__(self):return bool(self.c)
    def __eq__(self,v):
        if not isinstance(v,(N,int)):return False
        a,b,e=self.align(v);return a==b
    def __lt__(self,v):a,b,e=self.align(v);return a<b
    def __le__(self,v):a,b,e=self.align(v);return a<=b
    def __gt__(self,v):a,b,e=self.align(v);return a>b
    def __ge__(self,v):a,b,e=self.align(v);return a>=b
    def __str__(self):return '0' if not self.c else str(self.c)+(('e'+str(self.e)) if self.e else '')
    def ratio(self,other):
        if not other:return {'num':'0','den':'1'}
        a,b,e=self.align(other);g=gcd(a,b);a//=g;b//=g
        if b<0:a=-a;b=-b
        return {'num':str(a),'den':str(b)}
def parse(v):
    if type(v) is bool or type(v) is float:raise ValueError('NUMERIC_TYPE_REJECTED')
    if type(v) is int:q=N(v)
    elif isinstance(v,Decimal):
        if not v.is_finite():raise ValueError('NUMERIC_NONFINITE')
        t=v.as_tuple();q=N((-1 if t.sign else 1)*int(''.join(map(str,t.digits))),t.exponent)
    elif type(v) is str:
        if len(v)>2048 or not v.isascii() or not TOKEN.fullmatch(v):raise ValueError('NUMERIC_TOKEN_REJECTED')
        parts=re.split('[eE]',v);mant=parts[0];exp=int(parts[1]) if len(parts)>1 else 0
        sign=-1 if mant.startswith('-') else 1;mant=mant.lstrip('+-');digits=mant.replace('.','');places=len(mant.split('.')[1]) if '.' in mant else 0
        coefficient=sign*int(digits);q=N(coefficient,exp-places)
    else:raise ValueError('NUMERIC_TYPE_REJECTED')
    if q.c and (len(str(abs(q.c)))>256 or not -512<=q.e<=512):raise ValueError('NUMERIC_DOMAIN_REJECTED')
    return q
