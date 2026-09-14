"""Explicitly authorized READ-function setup. Capture itself never writes Excel."""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from phase57_source_capture import FIELDS, SAFETY, SHEETS, audit_workbook, read_snapshot, validate_config, require
from phase57_rss_raw import RAW_SHEETS, HEADERS, MARKET, layout, formulas

def config_for(path, symbols, rows=120):
    config=dict(schemaId='ARK_RSS_RAW_CONFIG_V1',mode='SOURCE_SEMANTICS_ONLY',
        workbookPath=str(path),workbookVersion='ARK_SOURCE_V1',sourceIdentity='MSII_RSS_RAW_V1',
        sheet='ARK_CHART_5M',range='A2:O3001',versionCell='B1',fields=FIELDS,safety=SAFETY,
        symbols=symbols,chartRows=rows,slots=layout(symbols,rows))
    validate_config(config)
    return config

def setup(workbook, config, backup_path):
    """Never touch an unknown workbook, order sheet, existing normalized table or app settings.
    On any failure keep the original backup and fail; never pretend partial setup succeeded.
    """
    audit_workbook(workbook,config)
    require(workbook.ReadOnly is False,'WORKBOOK_READ_ONLY')
    require(workbook.Date1904 is False,'DATE_SYSTEM_UNSUPPORTED')
    names={workbook.Worksheets(i).Name for i in range(1,workbook.Worksheets.Count+1)}
    if names & RAW_SHEETS:
        require(RAW_SHEETS.issubset(names),'PARTIAL_SETUP_REQUIRES_BACKUP_RESTORE')
        read_snapshot(workbook,config) # rerun only an identical verified layout
        return 'EXISTING_LAYOUT_VERIFIED'
    # SaveCopyAs is non-destructive; refuse overwrite at caller before any mutation.
    require(not Path(backup_path).exists(),'BACKUP_EXISTS')
    workbook.SaveCopyAs(str(backup_path))
    require(Path(backup_path).is_file(),'BACKUP_NOT_CREATED')
    for name in sorted(RAW_SHEETS):
        sheet=workbook.Worksheets.Add(After=workbook.Worksheets(workbook.Worksheets.Count))
        sheet.Name=name
    chart=workbook.Worksheets('ARK_RAW_CHART')
    market=workbook.Worksheets('ARK_RAW_MARKET')
    market.Range('A1:E1').Value2=(tuple(MARKET),)
    for slot in config['slots']:
        chart.Range(slot['header']).Value2=(tuple(HEADERS),)
    # Only these direct, official market-information functions are written.
    for (name,cell),formula in formulas(config['slots']).items():
        workbook.Worksheets(name).Range(cell).Formula=formula
    read_snapshot(workbook,config)
    workbook.Save()
    return 'RAW_LAYOUT_CREATED'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workbook',type=Path,required=True)
    parser.add_argument('--symbols',nargs='+',default=['7203.T'])
    parser.add_argument('--rows',type=int,default=120)
    args=parser.parse_args()
    require(args.workbook.suffix.lower()=='.xlsx','XLSX_REQUIRED')
    config=config_for(args.workbook.resolve(),args.symbols,args.rows)
    import win32com.client
    excel=win32com.client.GetActiveObject('Excel.Application')
    matches=[excel.Workbooks(i) for i in range(1,excel.Workbooks.Count+1)
        if str(excel.Workbooks(i).FullName).casefold()==config['workbookPath'].casefold()]
    require(len(matches)==1,'OPEN_DEDICATED_WORKBOOK_REQUIRED')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup=args.workbook.with_name(f'{args.workbook.stem}.before-rss-{stamp}.xlsx')
    status=setup(matches[0],config,backup)
    target=args.workbook.parent/'local-source.json'
    if target.exists():
        old=target.read_bytes()
        with target.with_name(f'local-source.before-{stamp}.json').open('xb') as out: out.write(old)
    temp=target.with_name(f'local-source.{stamp}.tmp')
    with temp.open('x',encoding='utf-8') as out:
        json.dump(config,out,ensure_ascii=False,indent=2);out.flush();os.fsync(out.fileno())
    os.replace(temp,target)
    evidence=dict(status=status,config=str(target),configSha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        workbookSha256=hashlib.sha256(args.workbook.read_bytes()).hexdigest(),backup=str(backup) if backup.exists() else None,
        sourceSemantics='UNVERIFIED',strategyCalculated=False,safety=SAFETY)
    with target.with_name(f'rss-setup-{stamp}.json').open('x',encoding='utf-8') as out: json.dump(evidence,out,indent=2)
    print(json.dumps(evidence))

if __name__=='__main__': main()
