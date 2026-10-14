"""Bounded, build-local reuse of already admitted causal source records.

No teacher or feature changes. A history extends only to the requested cutoff;
out-of-order requests use the original reader, never the later cached prefix.
"""
from collections import OrderedDict

from preopen_native_source import parse_ohlcv
from preopen_selector import PreopenError
from pathlib import Path
import os
import shutil
import sqlite3
from preopen_io import verify_entry,sha_file,write_json,SAFE_FLAGS


HISTORY_FIELDS = ("Date", "Code", "O", "H", "L", "C", "Vo", "Va",
                  "AdjFactor", "_sourceHash", "_ordinal")


class BuildReadCache:
    def __init__(self, store, calendar, *, max_securities=4096, max_prices=1500000):
        self.store = store
        self.reader = store.records
        self.availability_reader = store.available_at
        self.calendar = tuple(calendar)
        self.calendar_index = {d:i for i,d in enumerate(calendar)}
        self.calendar_set = set(calendar)
        self.max_securities, self.max_prices = max_securities, max_prices
        self.histories, self.prices = OrderedDict(), OrderedDict()
        self.availability, self.global_records, self.global_facts = {}, {}, {}

    def available_at(self, row, dataset):
        source = self.store.source(row["_sourceHash"])
        event = row[source.get("dateField", "Date")]
        clock = row["DiscTime"] if source["dataset"] == "FIN_SUMMARY" else None
        key = dataset, row["_sourceHash"], event, clock
        if key not in self.availability:
            self.availability[key] = self.availability_reader(row, dataset)
        return self.availability[key]

    def records(self, dataset, *, code=None, before=None, session=None):
        if dataset in ("TOPIX", "INVESTOR_TYPES") and code is None and before is None and session is None:
            if dataset not in self.global_records:
                # Rows remain their original strings. Numerical facts are still
                # constructed only after the per-session known-at filter.
                self.global_records[dataset] = list(self.reader(dataset))
            yield from self.global_records[dataset]
        else:
            yield from self.reader(dataset, code=code, before=before, session=session)

    @staticmethod
    def compact_history_row(row):
        return {k:row[k] for k in HISTORY_FIELDS if k in row}

    def daily_history(self, code, session):
        old = self.histories.get(code)
        if old is None or session < old[0]:
            rows = [self.compact_history_row(r) for r in self.reader("DAILY", code=code, before=session)]
            if old is not None:
                return rows
        else:
            previous, rows = old
            for d in self.calendar[self.calendar_index[previous]:self.calendar_index[session]]:
                rows.extend(self.compact_history_row(r) for r in self.reader("DAILY", code=code, session=d))
        self.histories[code] = session, rows
        self.histories.move_to_end(code)
        if len(self.histories) > self.max_securities:
            self.histories.popitem(last=False)
        return rows

    def price(self, row):
        if "_sourceHash" not in row or "_ordinal" not in row:
            return parse_ohlcv(row)
        key = row["_sourceHash"], row["_ordinal"]
        fingerprint = tuple(row.get(k) for k in ("O", "H", "L", "C", "Vo", "Va", "AdjFactor"))
        if key in self.prices:
            previous, parsed = self.prices[key]
            if previous != fingerprint:
                raise PreopenError("IMMUTABLE_PRICE_RECORD_CHANGED_WITHIN_BUILD")
            self.prices.move_to_end(key)
            return parsed
        parsed = parse_ohlcv(row)
        self.prices[key] = fingerprint, parsed
        if len(self.prices) > self.max_prices:
            self.prices.popitem(last=False)
        return parsed


def install_build_cache(store, calendar):
    cache = BuildReadCache(store, calendar)
    store.build_read_cache = cache
    store.records, store.available_at = cache.records, cache.available_at
    return cache


def price_row(store, row):
    cache = getattr(store, "build_read_cache", None)
    return cache.price(row) if cache is not None else parse_ohlcv(row)


def indexed_read_copies(source_directory, request, output):
    """Index separate derived copies; preserve both checkpoint databases."""
    private_root=Path(request['privateRoot']).resolve()
    target=output/'indexed_read_cache'
    target.mkdir(mode=0o700)
    changed=dict(request);receipts=[]
    paths=[('source',Path(source_directory)/'sources.sqlite',target/'source/sources.sqlite')]
    shared=request.get('existingDailySourceCache')
    if shared is not None:
        paths.append(('shared_daily',verify_entry(shared,private_root),target/'shared_daily/sources.sqlite'))
    for kind,original,destination in paths:
        original_hash,original_bytes=sha_file(original)
        destination.parent.mkdir(mode=0o700)
        shutil.copyfile(original,destination);os.chmod(destination,0o600)
        copied_hash,copied_bytes=sha_file(destination)
        if (copied_hash,copied_bytes)!=(original_hash,original_bytes):
            raise PreopenError('INDEXED_READ_COPY_BYTES_MISMATCH')
        connection=sqlite3.connect(destination)
        connection.execute('PRAGMA cache_size=-32768')
        connection.execute('CREATE INDEX IF NOT EXISTS lookup_session ON records(dataset,session,symbol,clock)')
        connection.commit()
        if connection.execute('PRAGMA quick_check').fetchone()[0]!='ok':
            raise PreopenError('INDEXED_READ_COPY_INTEGRITY')
        connection.close()
        derived_hash,derived_bytes=sha_file(destination)
        entry={'path':str(destination),'sha256':derived_hash,'bytes':derived_bytes}
        receipts.append({'kind':kind,'original':{'path':str(original),'sha256':original_hash,'bytes':original_bytes},
            'copyBeforeIndexSha256':copied_hash,'derived':entry,'onlyMutation':'CREATE_LOOKUP_SESSION_INDEX',
            'originalDatabaseModified':False,'logicalSourceRecordsChanged':False,'quickCheck':'PASS'})
        if kind=='shared_daily':changed['existingDailySourceCache']={**shared,**entry}
    receipt=write_json(target/'DERIVATION_RECEIPT.json',{'schema':'ARK_INDEXED_NATIVE_READ_DERIVATION_V1',
        'databases':receipts,'sourcePricesOrAdmissionChanged':False,**SAFE_FLAGS})
    return target/'source',changed,receipt
