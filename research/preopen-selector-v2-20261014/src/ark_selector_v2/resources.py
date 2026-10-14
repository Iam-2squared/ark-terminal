"""Stage resource measurements; RSS is process high-water, never file cache."""
from contextlib import contextmanager
import time
from typing import Any


def peak_rss_kib() -> int | None:
    try:
        import resource
        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except ImportError:
        return None


@contextmanager
def measure_stage(receipt: dict[str,Any], stage: str):
    wall=time.monotonic();cpu=time.process_time()
    try:
        yield
    finally:
        receipt[stage]={"wall_seconds":time.monotonic()-wall,"cpu_seconds":time.process_time()-cpu,
                        "process_peak_rss_kib":peak_rss_kib(),"rss_kind":"PROCESS_HIGH_WATER_NOT_INCREMENTAL_STAGE_MEMORY"}


def memory_preflight(fit_rows: int,cal_rows: int, *, ram_limit_bytes: int = 8*1024**3) -> dict[str,int]:
    from .exact_math import V2Error
    if fit_rows<0 or cal_rows<0:
        raise V2Error("NEGATIVE_PREFLIGHT_ROW_COUNT")
    # Conservative matrix/copy/workspace allowance plus estimator/tree overhead.
    matrix=(fit_rows+cal_rows)*95*8
    estimate=matrix*8+1080*31*128+256*1024**2
    if estimate>ram_limit_bytes:
        raise V2Error("BLOCKED_MEMORY_PREFLIGHT_FIT0")
    return {"matrix_bytes":matrix,"engineering_peak_estimate_bytes":estimate,"ram_limit_bytes":ram_limit_bytes}
