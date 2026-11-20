"""Exact v2 dated clock/source eligibility function slices."""
import math

def stamp(day, minute):
    return day + 'T%02d:%02d:00+09:00' % divmod(minute, 60)

def regular_end(day):
    return 900 if day < '2024-11-05' else 925

def session_close(day):
    return 900 if day < '2024-11-05' else 930

def regular_starts(day):
    return list(range(540, 690)) + list(range(750, regular_end(day)))

def active_minutes(day, start, end):
    return sum(max(0, min(end, b) - max(start, a)) for a, b in ((540, 690), (750, regular_end(day))))

def valid_raw(a):
    return len(a) == 7 and all(math.isfinite(float(x)) for x in a) and a[3] > 0 and a[3] <= min(a[1], a[4]) <= max(a[1], a[4]) <= a[2] and a[5] >= 0 and a[6] >= 0
