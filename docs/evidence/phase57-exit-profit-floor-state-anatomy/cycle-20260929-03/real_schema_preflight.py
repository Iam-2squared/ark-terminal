"""Read-only coverage/schema census on the frozen allowlisted Development paths."""
import importlib.util,json,math,pathlib,hashlib,collections,datetime
HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('phase57_anatomy_v3',HERE/'anatomy.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

def run():
    entries,funded,raw,skipped=a.load()
    type_count=collections.Counter(); reasons=collections.Counter(); sessions=collections.defaultdict(lambda:collections.Counter())
    raw_n=valid_n=auction_n=morning_auction_n=zero=missing_entries=duplicate_entries=invalid_auction=0
    entry_join=collections.Counter(); auction_shape=collections.Counter(); distinct=set()
    for arm in a.WORLD:
        for eid,e in entries[arm].items():
            entry_join[arm]+=1;op=e['opportunityId'];assert op in raw
            assert eid==f"{e['session']}|{e['symbol']}|{e['entryMinute']}"
            assert e['entryMinute'] in a.minutes() and e['session']>='2024-11-05'
            rows=raw[op];s=sessions[e['session']];seen=set();duplicate=False;owned=0;terminal=[]
            for row in rows:
                raw_n+=1;s['rawBarN']+=1
                key=type(row[0]).__name__ if isinstance(row,list) and row else 'missing'
                type_count[key]+=1
                minute,reason=a.canonical_minute(row)
                if reason:
                    reasons[reason]+=1;s['rejectedBarN']+=1;continue
                if minute in seen:
                    duplicate=True;reasons['DUPLICATE_TIMESTAMP']+=1;s['duplicateBarN']+=1
                seen.add(minute)
                if not a.valid(row,minute,auction=minute in (690,930)):
                    reasons['INVALID_OHLC_OR_AUCTION']+=1;s['invalidBarN']+=1
                    if minute==930:invalid_auction+=1
                    continue
                valid_n+=1;s['validBarN']+=1
                if minute==690:morning_auction_n+=1;s['morningAuctionN']+=1
                elif minute==930:
                    terminal.append(row);auction_n+=1;s['terminalAuctionN']+=1
                    auction_shape['singlePrice7Numeric']+=1
                elif minute>=e['entryMinute']:
                    owned+=1;s['postEntryValidContinuousN']+=1
            if duplicate:duplicate_entries+=1
            if not owned:zero+=1;s['zeroPostEntryBarEntryN']+=1
            if owned<len([m for m in a.minutes() if m>=e['entryMinute']]):missing_entries+=1;s['incompleteContinuousEntryN']+=1
            if not terminal:s['missingExactTerminalEntryN']+=1
            distinct.add(op)
    assert entry_join=={'IM':819,'R1':795}
    assert len(distinct)==len(raw)==819 and skipped==4556
    status='PASS'
    blockers=[]
    if raw_n==0 or valid_n==0 or zero==1614:blockers.append('EMPTY_BAR_PROJECTION')
    if set(type_count)-{'float'}:blockers.append('UNEXPECTED_TIMESTAMP_TYPE')
    if reasons.get('TIMESTAMP_FRACTIONAL',0) or reasons.get('TIMESTAMP_NONFINITE',0) or reasons.get('TIMESTAMP_TYPE',0):blockers.append('UNEXPECTED_TIMESTAMP_VALUE')
    if reasons.get('INVALID_OHLC_OR_AUCTION',0) or invalid_auction:blockers.append('UNHANDLED_BAR_FORMAT')
    if zero:blockers.append('ZERO_POST_ENTRY_BAR_ENTRY')
    if blockers:status='FAIL'
    return {'atJst':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
      'cycleIdentity':HERE.name,'basisHead':'1e328c7b47acf6dc9341e784808f691cdbd75f18',
      'status':status,'blockers':blockers,'realSchemaPreflightConsumed':1,'sourceHash':a.digest(a.ROOT/json.loads((HERE/'SOURCE_MANIFEST.json').read_text())['pins']['rawPath']['path']),
      'entryN':dict(entry_join),'uniquePathN':len(raw),'entryPathJoinN':sum(entry_join.values()),
      'parsedRawBarN':raw_n,'normalizedValidBarN':valid_n,'rejectedBarN':sum(reasons.values()),
      'rejectedBarCountByReason':dict(reasons),'timestampRawType':dict(type_count),
      'zeroBarEntryN':zero,'incompleteContinuousEntryN':missing_entries,'duplicateEntryN':duplicate_entries,
      'auction':{'exact930SinglePriceObservedAcrossEntriesN':auction_n,'morning690SinglePriceObservedAcrossEntriesN':morning_auction_n,'invalid930N':invalid_auction,'shape':dict(auction_shape),'missing930EntryN':sum(s['missingExactTerminalEntryN'] for s in sessions.values())},
      'sessionBarCount':{k:dict(v) for k,v in sorted(sessions.items())},
      'outOfAllowlistSkippedBeforeDecodeN':skipped,'outcomeMetricsComputed':False,
      'scopeNote':'counts per Entry, so shared IM/R1 opportunity path can be counted in both worlds; not independent samples'}

if __name__=='__main__':
    path=HERE/'REAL_SCHEMA_PREFLIGHT.json'
    if path.exists():raise FileExistsError(path)
    data=run();path.write_text(json.dumps(data,sort_keys=True,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:data[k] for k in ('status','blockers','entryN','parsedRawBarN','normalizedValidBarN','rejectedBarCountByReason','timestampRawType','zeroBarEntryN','incompleteContinuousEntryN','auction')},ensure_ascii=False))
