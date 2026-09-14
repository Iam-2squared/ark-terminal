"""Official RSS raw layout; source observations only, never bar finalization."""
import math
import re
from datetime import datetime, timedelta

RAW_SHEETS = {'ARK_RAW_CHART', 'ARK_RAW_MARKET'}
HEADERS = ['日付','時刻','始値','高値','安値','終値','出来高']
MARKET = ['現在日付','現在値詳細時刻','現在値','最良買気配値','最良売気配値']

def column(n):
    out=''
    while n:
        n,r=divmod(n-1,26); out=chr(65+r)+out
    return out

def layout(symbols, count=120):
    if not 1 <= len(symbols) <= 10 or len(set(symbols)) != len(symbols): raise ValueError('INVALID_SYMBOL_SET')
    if type(count) is not int or not 1 <= count <= 3000: raise ValueError('INVALID_ROW_COUNT')
    slots=[]
    for i,symbol in enumerate(symbols):
        if not re.fullmatch(r'\d{4,5}\.T',symbol): raise ValueError('INVALID_SOURCE_SYMBOL')
        a,g=column(i*9+1),column(i*9+7)
        slots.append(dict(slot=i,generation=0,symbol=symbol,sourceCode=symbol,
            header=f'{a}2:{g}2',chart=f'{a}3:{g}{count+2}',formulaCell=f'{a}1',
            chartFormula=f'=RssChart({a}2:{g}2,"{symbol}","5M",{count})',market=f'A{i+2}:E{i+2}'))
    return slots

def formulas(slots):
    out={('ARK_RAW_CHART',s['formulaCell']):s['chartFormula'] for s in slots}
    for s in slots:
        for j,field in enumerate(MARKET):
            out['ARK_RAW_MARKET',f'{column(j+1)}{s["slot"]+2}']=f'=RssMarket("{s["sourceCode"]}","{field}")'
    return out

def date_cell(value):
    if isinstance(value,bool): raise ValueError('DATE_BOOLEAN')
    if isinstance(value,(int,float)) and math.isfinite(value) and value == int(value):
        return (datetime(1899,12,30)+timedelta(days=value)).date().isoformat()
    if isinstance(value,str) and re.fullmatch(r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',value):
        return datetime.strptime(value.replace('/','-'),'%Y-%m-%d').date().isoformat()
    raise ValueError('DATE_PARSE')

def time_cell(value):
    if isinstance(value,bool): raise ValueError('TIME_BOOLEAN')
    if isinstance(value,(int,float)) and math.isfinite(value) and 0 <= value < 1:
        sec=round(value*86400)
        if sec >= 86400 or abs(value*86400-sec) > .001: raise ValueError('TIME_PRECISION')
        return f'{sec//3600:02d}:{sec//60%60:02d}:{sec%60:02d}'
    if isinstance(value,str) and re.fullmatch(r'\d{1,2}:\d{2}(:\d{2})?',value):
        return datetime.strptime(value,'%H:%M:%S' if value.count(':')==2 else '%H:%M').strftime('%H:%M:%S')
    raise ValueError('TIME_PARSE')

def number_cell(value):
    if isinstance(value,bool): raise ValueError('NUMERIC_BOOLEAN')
    if isinstance(value,(int,float)) and math.isfinite(value): return value
    if isinstance(value,str) and re.fullmatch(r'-?\d+(\.\d+)?',value):
        parsed=float(value)
        if math.isfinite(parsed): return parsed
    raise ValueError('NUMERIC_PARSE')

def normalize(raw, slots, session_date):
    """Keep raw snapshots separately. Invalid cells remain explicit, never filled.

    RssMarket snapshot is capture-time diagnostic, NOT a historical quote for each bar.
    Historical chart rows are retained in raw evidence, excluded from today's observer.
    """
    result=[]
    for s,data in zip(slots,raw,strict=True):
        market=data['market'][0]
        if len(market)!=5: raise ValueError('PARTIAL_MARKET_ROW')
        try: mt=f'{date_cell(market[0])}T{time_cell(market[1])}+09:00'
        except (ValueError,OverflowError): mt='#INVALID_MARKET_TIMESTAMP'
        quotes=[]
        for v in market[2:]:
            try: quotes.append(number_cell(v))
            except ValueError: quotes.append('#INVALID_QUOTE')
        for row in data['chart']:
            if all(v in (None,'') for v in row): continue
            if len(row)!=7: raise ValueError('PARTIAL_CHART_ROW')
            try: day=date_cell(row[0])
            except (ValueError,OverflowError): day='#INVALID_DATE'
            if not day.startswith('#') and day != session_date: continue
            try: clock=time_cell(row[1])
            except ValueError: clock='#INVALID_TIME'
            values=[]
            for v in row[2:]:
                try: values.append(number_cell(v))
                except ValueError: values.append('#INVALID_NUMERIC')
            result.append([s['slot'],s['generation'],s['symbol'],s['sourceCode'],day,clock,*values,mt,*quotes])
    return result
