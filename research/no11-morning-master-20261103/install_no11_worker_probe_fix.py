#!/usr/bin/env python3
"""Versioned, durable live-PC installer for DATA-only worker-probe correction.

Original resilience-tools package and signed legacy install journal are never
changed. A NEW versioned package (worker + identical original validator) is
published, then the SINGLE pinned binding is atomically updated. The existing
Run-No11NightlyCycle.ps1 wrapper already follows this binding; no UI or Trade
script changes. A known, verified source and all quiet-process checks are
required before application. Does not execute RSS or trading.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

import no11_nightly_resume as original
import no11_nightly_resume_workeraware as corrected

VERSION = "ARK_NO11_WORKER_PROBE_V2_INSTALL"
MARKER = "ARK_NO11_NIGHTLY_RESUME_WORKER_PROBE_V2"
ORIGINAL_FILE = "no11_nightly_resume.py"
CORRECTED_FILE = "no11_nightly_resume_workeraware.py"
VALIDATOR_FILE = "no11_selection_status.py"
WRAPPER_FILE = "Run-No11ResumableNightly.ps1"
JOURNAL = "worker-probe-v2-transaction.json"


def require(condition, code):
    if not condition:
        raise ValueError("NO11_WORKER_PROBE_INSTALL_" + code)


def safe(path, directory=False):
    return original.safe(path, directory)


def digest(raw):
    return original.digest(raw)


def ensure_same_except_probe(prior, next_bytes):
    b = prior.decode("utf-8-sig").replace("\r\n", "\n")
    a = next_bytes.decode("utf-8-sig").replace("\r\n", "\n")
    start="def no_workers():"
    stop="\ndef run_logged("
    require(b.count(start) == a.count(start) == 1
            and b.count(stop) == a.count(stop) == 1,
            "SOURCE_STRUCTURE_CHANGED")
    b1,b2=b.index(start),b.index(stop,b.index(start))
    a1,a2=a.index(start),a.index(stop,a.index(start))
    require(b[:b1] == a[:a1] and b[b2:] == a[a2:]
            and MARKER in a[a1:a2] and "OLD_WORKER_RUNNING_OR_QUERY_FAILED" in b[b1:b2]
            and "OLD_WORKER_STILL_RUNNING" in a[a1:a2]
            and "WORKER_QUERY_FAILED" in a[a1:a2],
            "SOURCE_PATCH_NOT_LIMITED_TO_PROCESS_PROBE")
    compile(next_bytes.decode("utf-8-sig"), CORRECTED_FILE, "exec")


def local_inputs(store, source):
    store = safe(store, True)
    source = safe(source, True)
    binding_path = safe(store / "automatic-inputs.json")
    b = original.read(binding_path)
    require(b.get("schemaId") == "ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1"
            and b.get("orderTransmission") is False
            and b.get("manualPriceInputRequired") is False
            and b.get("manualEvidenceRequired") is False,
            "BINDING_CONTRACT")
    settings=original.read(safe(store / "settings.json"))
    require(settings.get("normalMaxPositions") == 3
            and settings.get("sameDayApprovalRequired") is True
            and settings.get("automaticOrderAuthorization") is False
            and settings.get("orderTransmission") is False,
            "TRADING_SETTINGS_UNCHANGED")
    old_path = safe(Path(b["nightlyResumeTool"]))
    validator_path = safe(old_path.with_name(VALIDATOR_FILE))
    require(digest(old_path.read_bytes()) == b.get("nightlyResumeToolSha256")
            and digest(validator_path.read_bytes()) == b.get("nightlyResumeValidatorSha256"),
            "BOUND_SOURCE_HASH_CHANGED")
    wrapper=safe(Path(b["engine"]) / "windows" / "Run-No11NightlyCycle.ps1")
    wrapper_ref=safe(source / WRAPPER_FILE)
    require(wrapper.read_bytes() == wrapper_ref.read_bytes()
            and b"nightlyResumeToolSha256" in wrapper.read_bytes(),
            "INSTALLED_WRAPPER_CHANGED")
    gui=safe(store / "oneclick" / "Start-No11OneClick.ps1")
    old_source=safe(source / ORIGINAL_FILE).read_bytes()
    new_source=safe(source / CORRECTED_FILE).read_bytes()
    ensure_same_except_probe(old_source, new_source)
    require(old_path.read_bytes() == old_source,
            "OLD_PACKAGE_NOT_OFFICIAL_SOURCE")
    return b, binding_path, old_path, validator_path, gui, new_source


def quiet():
    corrected.no_workers()
    # Exclude only our own CIM query shell; block an open WHITE OneClick UI,
    # even though it is DATA-only, because binding change must be atomic.
    script=r"""$ErrorActionPreference='Stop';try{
 $live=@(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
  $_.ProcessId -ne $PID -and
  $_.Name -match '^(?:powershell|pwsh)(?:[.]exe)?$' -and
  [string]$_.CommandLine -match 'Start-No11OneClick[.]ps1|Start-No11PreopenStandby[.]ps1'
 })
 if($live.Count){exit 3};exit 0
}catch{exit 4}"""
    with tempfile.TemporaryDirectory(prefix="no11-ui-closed-") as tmp:
        p=Path(tmp)/"read-only-ui-check.ps1"
        p.write_text(script, encoding="utf-8")
        try:
            r=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive",
                              "-ExecutionPolicy","Bypass","-File",str(p)],
                             capture_output=True,timeout=35,check=False)
        except (OSError, subprocess.TimeoutExpired):
            require(False,"UI_QUERY_FAILED")
    if r.returncode==3:
        require(False,"CLOSE_ONECLICK_UI")
    require(r.returncode==0,"UI_QUERY_FAILED")


def immutable(path, raw):
    require(safe(path.parent,True), "PACKAGE_DIR")
    if path.exists() or path.is_symlink():
        require(safe(path).read_bytes()==raw,"PACKAGE_ALREADY_EXISTS_DIFFERENT")
        return
    temp=None
    try:
        with tempfile.NamedTemporaryFile("wb",dir=path.parent,delete=False) as fp:
            temp=Path(fp.name)
            fp.write(raw)
            fp.flush()
            os.fsync(fp.fileno())
        try:
            os.link(temp,path)
        except FileExistsError:
            require(safe(path).read_bytes()==raw,"PACKAGE_RACE")
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def replace(path, before, after):
    require(safe(path).read_bytes()==before,"CONCURRENT_BINDING_EDIT")
    temp=None
    try:
        with tempfile.NamedTemporaryFile("wb",dir=path.parent,delete=False) as fp:
            temp=Path(fp.name)
            fp.write(after)
            fp.flush()
            os.fsync(fp.fileno())
        require(path.read_bytes()==before,"CONCURRENT_BINDING_EDIT")
        os.replace(temp,path)
        temp=None
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def verify_journal(store, journal, binding, gui, do_apply, test=False):
    if not journal.exists():
        return None
    j=original.checkpoint(journal)
    require(j.get("kind")==VERSION
            and j.get("whiteGuiSha256")==digest(gui.read_bytes())
            and j.get("orderTransmission") is False
            and j.get("phase") in ("PREPARED","COMPLETE"),
            "JOURNAL_INVALID")
    before=base64.b64decode(j["bindingBefore"],validate=True)
    after=base64.b64decode(j["bindingAfter"],validate=True)
    require(digest(before)==j["bindingBeforeSha256"]
            and digest(after)==j["bindingAfterSha256"],
            "JOURNAL_HASH")
    require(binding.read_bytes() in (before,after),"BINDING_EXTERNAL_EDIT")
    worker_path=safe(j["workerTool"])
    validator_path=safe(j["workerValidator"])
    require(digest(worker_path.read_bytes())==j["workerToolSha256"]
            and digest(validator_path.read_bytes())==j["validatorSha256"],
            "PUBLISHED_TOOL_CHANGED")
    if j["phase"]=="COMPLETE":
        require(binding.read_bytes()==after,"COMPLETE_BINDING_REVERTED")
        return "ALREADY_APPLIED"
    require(do_apply,"INCOMPLETE_APPLY_REQUIRED")
    if not test:
        quiet()
    if binding.read_bytes()==before:
        replace(binding,before,after)
    j["phase"]="COMPLETE"
    original.atomic(journal,j)
    require(binding.read_bytes()==after,"POSTRESTART_BINDING_READBACK")
    return "PASS"


def install(store,source,do_apply=False,test=False):
    store=safe(store,True)
    with original.exclusive(store/"worker-probe-v2-installer.lock"):
        bind_path=safe(store/"automatic-inputs.json")
        gui=safe(store/"oneclick/Start-No11OneClick.ps1")
        journal=store/JOURNAL
        if journal.exists():
            status=verify_journal(store,journal,bind_path,gui,do_apply,test)
            print("NO11_WORKER_PROBE_JOURNAL="+status,flush=True)
            return status
        b,bind_path,old_tool,validator,gui,new_source=local_inputs(store,source)
        before=bind_path.read_bytes()
        gui_sha=digest(gui.read_bytes())
        new_sha=digest(new_source)
        package=store/("worker-probe-v2-"+new_sha[:20])
        new_tool=package/CORRECTED_FILE
        new_validator=package/VALIDATOR_FILE
        new=dict(b,nightlyResumeTool=str(new_tool),
                 nightlyResumeToolSha256=new_sha)
        after=original.encode(new)
        require(after!=before,"NO_CHANGE")
        print("NO11_WORKER_PROBE_SOURCE=ORIGINAL_BINDING_VERIFIED",flush=True)
        print("NO11_WORKER_PROBE_NEW_TOOL_SHA256="+new_sha,flush=True)
        if not do_apply:
            return "READY"
        if not test:
            quiet()
        if not package.exists():
            package.mkdir(mode=0o700)
        safe(package,True)
        immutable(new_tool,new_source)
        immutable(new_validator,validator.read_bytes())
        require(digest(gui.read_bytes())==gui_sha
                and bind_path.read_bytes()==before,"PRECOMMIT_EDIT")
        j={"schemaId":original.SCHEMA,"kind":VERSION,"phase":"PREPARED",
           "whiteGuiSha256":gui_sha,
           "bindingBefore":base64.b64encode(before).decode("ascii"),
           "bindingAfter":base64.b64encode(after).decode("ascii"),
           "bindingBeforeSha256":digest(before),
           "bindingAfterSha256":digest(after),
           "workerTool":str(new_tool),"workerToolSha256":new_sha,
           "workerValidator":str(new_validator),
           "validatorSha256":digest(validator.read_bytes()),
           "orderTransmission":False}
        original.atomic(journal,j)
        replace(bind_path,before,after)
        require(bind_path.read_bytes()==after
                and digest(gui.read_bytes())==gui_sha,"BINDING_READBACK")
        j["phase"]="COMPLETE"
        original.atomic(journal,j)
        return "PASS"


def main():
    arg=argparse.ArgumentParser(description=__doc__)
    arg.add_argument("--store",required=True,type=Path)
    arg.add_argument("--source-dir",required=True,type=Path)
    arg.add_argument("--apply",action="store_true")
    a=arg.parse_args()
    try:
        require(os.name=="nt","WINDOWS_ONLY")
        print("NO11_WORKER_PROBE_INSTALL="+install(a.store,a.source_dir,a.apply))
        print("ACTUAL_RSS_CAPTURE_STARTED=False")
        print("WEEKLY_MAX47_UNCHANGED=True")
        print("WHITE_GUI_CHANGED=False")
        print("ORIGINAL_TOOL_PACKAGE_PRESERVED=True")
        print("TRADE_LAUNCHED=False")
        print("ORDER_TRANSMISSION=False")
    except Exception as exc:
        code=str(exc)
        if not re.fullmatch(r"NO11_[A-Z0-9_]+",code):
            code="NO11_WORKER_PROBE_INSTALL_UNVERIFIED_SOURCE_OR_RUNTIME"
        print("NO11_WORKER_PROBE_INSTALL=BLOCKED|"+code)
        print("TRADE_LAUNCHED=False")
        print("ORDER_TRANSMISSION=False")
        raise SystemExit(2)


if __name__=="__main__":
    main()
