#!/usr/bin/env python3
"""Bind the *actual three saved workbooks* for future LIVE preflight only.

Does not approve orders, create dated master evidence, bypass frozen ENTRY/EXIT,
remap a signed 2026-11-10 handoff, rewrite Excel workbooks or transmit trades.
"""
from __future__ import annotations
import json
from pathlib import Path
import re

MARK='ARK_NO11_LIVE_XLSB_THREE_BOOK_PRECHECK_V1'
ROLE={'Account':('accountWorkbookPath','ARK_ACCOUNT_READONLY'),
      'Market':('marketWorkbookPath','ARK_MARKET_READONLY'),
      'OrderIds':('orderIdWorkbookPath','ARK_ORDER_IDS_READONLY')}
ALLOWED={'.xlsb','.xlsx','.xlsm'}

def need(ok,code):
    if not ok:raise ValueError('NO11_LIVE_XLSB_'+code)

def checked_registration(reg):
    need(type(reg) is dict and
         reg.get('schemaId')=='ARK_NO11_DATA_WORKBOOK_REGISTRATION_V1' and
         reg.get('orderTransmission') is False,'REGISTRY')
    books=reg.get('books')
    need(type(books) is list and len(books)==3,'THREE_REGISTRY_BOOKS')
    by_role={}
    names=set()
    for row in books:
        need(type(row) is dict,'REGISTRY_ROW')
        role=row.get('role')
        need(role in ROLE and role not in by_role,'REGISTRY_ROLE')
        path=row.get('path')
        need(type(path) is str and Path(path).is_absolute() and
             Path(path).suffix.lower() in ALLOWED and
             row.get('sheet')==ROLE[role][1] and
             row.get('date1904') is False and
             row.get('name')==Path(path).name and
             Path(path).name.casefold() not in names,'REGISTERED_PATH')
        # The registered on-disk bytes MUST exist; never generate a workbook.
        need(Path(path).is_file() and not Path(path).is_symlink(),'REGISTERED_BOOK_MISSING')
        names.add(Path(path).name.casefold())
        by_role[role]=path
    need(len(by_role)==3,'REGISTERED_THREE_UNIQUE')
    return by_role

def safe_settings_change(settings,by_role):
    need(type(settings) is dict and
         settings.get('schemaId')=='ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1' and
         settings.get('normalMaxPositions')==3 and
         settings.get('sameDayApprovalRequired') is True and
         settings.get('automaticOrderAuthorization') is False and
         settings.get('orderTransmission') is False,'LIVE_SETTINGS_MODE')
    output=dict(settings)
    for role,(field,_) in ROLE.items():
        original=output.get(field)
        need(type(original) is str and
             (not original or Path(original).is_absolute()),'CURRENT_PATH_FORMAT')
        # User may already have manually selected correct original workbook.
        # Old .xlsx references are not proof that old workbook is open.
        output[field]=by_role[role]
    need(all(output.get(k)==v for k,v in settings.items() if
             k not in {x[0] for x in ROLE.values()}),'UNRELATED_LIVE_SETTINGS')
    return output

def transform_settings_key_order(raw):
    """n.encode sorts JSON keys; key order is not a settings value.

    Change only the exact field-name comparison, retaining the same required
    fields, case sensitivity, MAX3 and all approval/transmission checks.
    """
    old=b"(@($cfg.PSObject.Properties.Name) -join '|') -ceq ($required -join '|')"
    new=b"(@($cfg.PSObject.Properties.Name | Sort-Object -CaseSensitive) -join '|') -ceq (@($required | Sort-Object -CaseSensitive) -join '|')"
    if raw.count(new)==1 and old not in raw:
        return raw
    need(raw.count(old)==1 and new not in raw,'SETTINGS_COMPARATOR_SOURCE_CHANGED')
    return raw.replace(old,new,1)

def transform_launcher(raw):
    # Must run before the XLSB idempotence return: already enrolled PCs may
    # still carry the old order-sensitive comparison.
    raw=transform_settings_key_order(raw)
    bom=raw.startswith(b'\xef\xbb\xbf')
    source=raw.decode('utf-8-sig')
    newline='\r\n' if '\r\n' in source else '\n'
    src=source.replace('\r\n','\n')
    if MARK in src:return raw
    original=""" $a=LocalFile $cfg.accountWorkbookPath 'ACCOUNT_XLSX'
 $b=LocalFile $cfg.marketWorkbookPath 'MARKET_XLSX'
 $files=@($a,$b)
 if($live){$files+=@(LocalFile $cfg.orderIdWorkbookPath 'ORDER_ID_XLSX')}"""
    replacement=""" # ARK_NO11_LIVE_XLSB_THREE_BOOK_PRECHECK_V1
 # Exact three original paths from settings, no filename .xlsx assumptions.
 # This is a preflight only; never authorizes or sends an order.
 $a=LocalFile $cfg.accountWorkbookPath 'ACCOUNT_BOOK'
 $b=LocalFile $cfg.marketWorkbookPath 'MARKET_BOOK'
 $c=LocalFile $cfg.orderIdWorkbookPath 'ORDER_ID_BOOK'
 $files=@($a,$b,$c)"""
    a="$account=$excel.Workbooks.Item('Ark_No11_MSII_RSS.xlsx').Worksheets.Item('ARK_ACCOUNT_READONLY')"
    b="$market=$excel.Workbooks.Item('Ark_No11_MARKET_RSS.xlsx').Worksheets.Item('ARK_MARKET_READONLY')"
    need(src.count(original)==1 and src.count(a)==1 and src.count(b)==1,
         'LAUNCHER_SOURCE_UNRECOGNIZED')
    src=src.replace(original,replacement,1)
    src=src.replace(a,"$account=$excel.Workbooks.Item([IO.Path]::GetFileName($a)).Worksheets.Item('ARK_ACCOUNT_READONLY')",1)
    src=src.replace(b,"$market=$excel.Workbooks.Item([IO.Path]::GetFileName($b)).Worksheets.Item('ARK_MARKET_READONLY')",1)
    need(src.count('$ids=$excel.Workbooks.Item([IO.Path]::GetFileName($cfg.orderIdWorkbookPath))')==1,
         'ORDER_IDS_LOOKUP_CHANGED')
    src=src.replace('$ids=$excel.Workbooks.Item([IO.Path]::GetFileName($cfg.orderIdWorkbookPath))',
                    '$ids=$excel.Workbooks.Item([IO.Path]::GetFileName($c))',1)
    # For BOTH Weekly/DATA and approved Trade, exact 3 originals.
    # A new LIVE order is still gated by existing dated config, evidence and
    # user approval checks; none of that code is modified.
    need("Need ($excel.Workbooks.Count -eq $files.Count) 'EXCEL_BOOK_COUNT'" in src,
         'STRICT_BOOK_COUNT_MISSING')
    need(src.count(MARK)==1 and
         "Need $approved 'TODAYS_EXPLICIT_OPERATOR_APPROVAL_REQUIRED'" in src and
         "Need ($broker.transport.mode -ceq 'LIVE'" in src and
         "StartChild 'TRADE' $trade $params $sha $day" in src and
         "normalMaxPositions=3" in src,'FROZEN_TRADE_GUARDS_CHANGED')
    return (b'\xef\xbb\xbf' if bom else b'')+src.replace('\n',newline).encode('utf-8')


OPERATOR_MARK='ARK_NO11_LIVE_XLSB_OPERATOR_FORMAT_V1'

def transform_operator(raw):
    """Only allow the originally supported Excel formats, including XLSB.

    Existing one-day live operator approval, original MAX3, 100-share lots,
    non-margin securities cash and frozen controller remain byte-identical.
    """
    bom=raw.startswith(b'\xef\xbb\xbf')
    source=raw.decode('utf-8-sig')
    newline='\r\n' if '\r\n' in source else '\n'
    text=source.replace('\r\n','\n')
    if OPERATOR_MARK in text:return raw
    before=""" Need ($AccountWorkbookPath -cne $OrderIdWorkbookPath -and
       $AccountWorkbookPath.EndsWith('.xlsx',[StringComparison]::OrdinalIgnoreCase) -and
       $OrderIdWorkbookPath.EndsWith('.xlsx',[StringComparison]::OrdinalIgnoreCase)) 'WORKBOOK_PAIR_INVALID'"""
    after=""" # ARK_NO11_LIVE_XLSB_OPERATOR_FORMAT_V1: accepted Excel container formats
 # only. Both books must remain different exact local paths with original
 # saved config, broker, same-day approval and all physical guards unchanged.
 Need ($AccountWorkbookPath -cne $OrderIdWorkbookPath -and
       ([IO.Path]::GetExtension($AccountWorkbookPath).ToLowerInvariant() -in @('.xlsx','.xlsb','.xlsm')) -and
       ([IO.Path]::GetExtension($OrderIdWorkbookPath).ToLowerInvariant() -in @('.xlsx','.xlsb','.xlsm'))) 'WORKBOOK_PAIR_INVALID'"""
    need(text.count(before)==1,'OPERATOR_FORMAT_SOURCE_CHANGED')
    output=text.replace(before,after,1)
    for pin in (
        "Need $IApproveFullArkLiveOrdersForThisSession.IsPresent 'SAME_DAY_OPERATOR_APPROVAL_REQUIRED'",
        "'BROKER_LIVE_CONFIG_REQUIRED'","'REVIEWED_SECURITIES_ONLY_CASH'",
        "'TRANSPORT_SESSION_APPROVAL'","'MAX3_AND_SECURITIES_CASH'",
        "'FULL_FROZEN_PREFLIGHT_BLOCKED'"):
        need(pin in output,'OPERATOR_FROZEN_GUARD_MISSING')
    need(output.count(OPERATOR_MARK)==1 and
         output.count('--operator-approved-broker-live')>=2 and
         output.count("if($PreflightOnly)")>=2,
         'OPERATOR_FROZEN_STATE_CHANGED')
    return (b'\xef\xbb\xbf' if bom else b'')+output.replace('\n',newline).encode('utf-8')
