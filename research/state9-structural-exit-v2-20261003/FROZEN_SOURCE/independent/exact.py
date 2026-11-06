"""Independent lexical admission, Fraction storage, separate factor serializer."""
import re
from decimal import Decimal
from fractions import Fraction
LEX=re.compile(r'[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[Ee][-+]?[0-9]+)?',re.ASCII)
def parse(v):
    if type(v) is int:d=Decimal(v)
    elif type(v) is Decimal:d=v
    elif type(v) is str:
        if len(v)>2048 or not v.isascii() or LEX.fullmatch(v) is None:raise ValueError('NUMERIC_TOKEN_REJECTED')
        # Canonical admission BEFORE constructing Decimal. A lexical zero has
        # canonical exponent zero even if its written exponent exceeds the
        # platform Decimal constructor's exponent range. Nonzero out-of-domain
        # exponents are expected input rejection, not engine arithmetic faults.
        pieces=re.split('[Ee]',v);mantissa=pieces[0].lstrip('+-')
        significant=mantissa.replace('.','').lstrip('0')
        if not significant:return Fraction(0)
        suffix_zeros=len(significant)-len(significant.rstrip('0'))
        fractional_places=len(mantissa.split('.')[1]) if '.' in mantissa else 0
        canonical_exponent=(int(pieces[1]) if len(pieces)>1 else 0)-fractional_places+suffix_zeros
        if len(significant)-suffix_zeros>256 or canonical_exponent < -512 or canonical_exponent>512:
            raise ValueError('NUMERIC_DOMAIN_REJECTED')
        d=Decimal(v)
    else:raise ValueError('NUMERIC_TYPE_REJECTED')
    if not d.is_finite():raise ValueError('NUMERIC_NONFINITE')
    sign,digits,e=d.as_tuple();n=0
    for digit in digits:n=10*n+digit
    if not n:return Fraction(0)
    while n%10==0:n//=10;e+=1
    if len(str(n))>256 or e < -512 or e>512:raise ValueError('NUMERIC_DOMAIN_REJECTED')
    n=-n if sign else n
    return Fraction(n*10**e) if e>=0 else Fraction(n,10**(-e))
def price(x):
    if not x:return '0'
    n,d=x.numerator,x.denominator;a=b=0
    while d%2==0:a+=1;d//=2
    while d%5==0:b+=1;d//=5
    if d!=1:raise ArithmeticError('NONDECIMAL_PRICE')
    k=max(a,b);n*=2**(k-a)*5**(k-b);e=-k
    while n%10==0:n//=10;e+=1
    return str(n)+(('e'+str(e)) if e else '')
def ratio(x,y):
    f=abs(x)/y if y else Fraction(0)
    return {'num':str(f.numerator),'den':str(f.denominator)}
