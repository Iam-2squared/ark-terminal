"""Shared RSS display placeholders, extracted unchanged from Phase58."""
RSS_DASH_PLACEHOLDER_CHARS = frozenset("-‐‑‒–—−－")


def is_rss_display_placeholder(value):
    text = str(value).strip() if value is not None else ""
    return text == "" or all(char in RSS_DASH_PLACEHOLDER_CHARS for char in text)


def unpopulated_ohlcv_reason(values, parse_number):
    """Narrow source-gate allowlist; caller validates timestamp before skipping.

    Phase58 recognizes blank and dash displays. This gate accepts only homogeneous
    blank OHLC or homogeneous dash OHLC, and never hides malformed volume.
    """
    ohlc, volume = values[:4], values[4]
    blank = lambda value: value is None or isinstance(value, str) and not value.strip()
    dash = lambda value: not blank(value) and is_rss_display_placeholder(value)
    volume_blank = blank(volume)
    volume_dash = dash(volume)
    volume_zero = False if volume_blank or volume_dash else parse_number(volume) == 0
    if all(blank(value) for value in ohlc) and (volume_blank or volume_zero):
        return "UNPOPULATED_BLANK_OHLC"
    if all(dash(value) for value in ohlc) and (volume_blank or volume_dash or volume_zero):
        return "UNPOPULATED_DASH_OHLC"
    return None
