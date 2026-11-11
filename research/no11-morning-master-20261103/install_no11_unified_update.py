#!/usr/bin/env python3
"""Single transactional entry for native weekly/daily and interruption repair.

Install order: verified resumption backend -> exact-source 47-slot launcher.
Both phases retain independent permanent rollback journals. If interrupted,
re-run THIS SAME command; prior complete work is verified, not replayed.
This never invokes the broker, actual RSS capture, or trading engine.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import os
import re
import sys
import no11_nightly_resume as n
import install_no11_week_resilience as core
import install_no11_launcher_update as launcher

def need(ok, code):
    if not ok:
        raise ValueError('NO11_UNIFIED_REFRESH_' + code)

def run(store,source,apply=False,_test=False):
    store=n.safe(store,True)
    with n.exclusive(store/'unified-refresh-install.lock'):
        if not apply:
            backend=core.install(store,source,False)
            frontend=launcher.install(store,do_apply=False,_test=_test) if backend=='ALREADY_APPLIED' else 'WAIT_FOR_BACKEND_INSTALL'
            return backend,frontend
        backend=core.install(store,source,True)
        print('NO11_BASE_RESUME_INSTALL='+backend,flush=True)
        # Backend is already durable: if launcher installation is interrupted
        # a future invocation sees ALREADY_APPLIED then resumes the launcher.
        frontend=launcher.install(store,do_apply=True,_test=_test)
        return backend,frontend

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store',type=Path,required=True)
    parser.add_argument('--source-dir',type=Path,default=Path(__file__).parent)
    parser.add_argument('--apply',action='store_true')
    opts=parser.parse_args(argv)
    try:
        need(os.name=='nt','WINDOWS_ONLY')
        a,b=run(opts.store,opts.source_dir,opts.apply)
        print('NO11_BASE_RESUME_INSTALL='+a)
        print('NO11_NATIVE_LAUNCHER_MAX47_INSTALL='+b)
        print('NO11_ONECLICK_WEEKEND_DATA_UPDATE_AVAILABLE='+str(b in ('PASS','ALREADY_APPLIED')))
        print('NO11_WEEKLY_DAILY_1M_PHYSICAL_MAX=47_MINUS_ORIGINAL_CHARTS')
        print('NO11_WEEKLY_RESUME_WITHOUT_RESETTING_REQUEST=True')
    except Exception as e:
        reason=str(e)
        if not re.fullmatch(r'NO11_[A-Z0-9_]+',reason):
            reason='NO11_UNIFIED_REFRESH_SOURCE_OR_LOCAL_RUNTIME_UNVERIFIED'
        print('NO11_UNIFIED_REFRESH=BLOCKED|'+reason)
        raise SystemExit(2)
    finally:
        print('WHITE_ONECLICK_GUI_MODIFIED=False')
        print('FROZEN_STRATEGIES_MODIFIED=False')
        print('TRADE_LAUNCHED=False')
        print('ORDER_TRANSMISSION=False')

if __name__=='__main__':
    main()
