from dataclasses import dataclass

def direction(closes):
    if not closes: return None
    if closes[-1] > closes[0]: return "UP"
    if closes[-1] < closes[0]: return "DOWN"
    return "UNCHANGED"

def structure_from_pivots(pivots, current_close):
    highs=[p for p in pivots if p["kind"]=="H"]
    lows=[p for p in pivots if p["kind"]=="L"]
    if len(highs)<2 or len(lows)<2:
        return {"value":None,"status":"NOT_OBSERVABLE"}
    up = highs[-1]["price"] > highs[-2]["price"] and lows[-1]["price"] > lows[-2]["price"]
    down = highs[-1]["price"] < highs[-2]["price"] and lows[-1]["price"] < lows[-2]["price"]
    if up and down:
        return {"value":None,"status":"AMBIGUOUS"}
    if up:
        protected=lows[-1]["price"]
        if current_close < protected:
            return {"value":None,"status":"INVALIDATED","protected":protected}
        return {"value":"UP_STRUCTURE","status":"IDENTIFIED","protected":protected}
    if down:
        protected=highs[-1]["price"]
        if current_close > protected:
            return {"value":None,"status":"INVALIDATED","protected":protected}
        return {"value":"DOWN_STRUCTURE","status":"IDENTIFIED","protected":protected}
    return {"value":None,"status":"UNRESOLVED"}

def phase(parent_structure, latest_dir, invalidated=False, recovery=None, range_identified=False):
    out=[]
    if invalidated:
        out.append("RESTRUCTURING")
        return out
    if range_identified:
        out.append("BALANCE")
    if parent_structure=="UP_STRUCTURE":
        out.append("PROGRESSION" if latest_dir=="UP" else "CORRECTION" if latest_dir=="DOWN" else "BALANCE")
    elif parent_structure=="DOWN_STRUCTURE":
        out.append("PROGRESSION" if latest_dir=="DOWN" else "CORRECTION" if latest_dir=="UP" else "BALANCE")
    if recovery is not None and recovery>0:
        out.append("RECOVERY")
    return sorted(set(out))

def breakout(previous_close, current_close, high, level):
    if high > level and current_close <= level:
        return "WICK_TOUCH_UP"
    if previous_close <= level < current_close:
        return "CLOSE_CROSS_UP"
    return None
