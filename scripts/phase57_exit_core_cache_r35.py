"""Create a reusable unscaled R35 CORE matrix from the immutable R20 observer.

No fit, labels, policy replay or performance. All 2,155 IDs/arm stay in the
copied Entry envelopes, including no-entry rows. Only pinned R20 inputs are read.
"""
from __future__ import annotations
import argparse
import collections
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile
from scripts.phase57_exit_core_runtime_r35 import CoreEncoder

R20_ZIP_SHA = '6019809ca4ac9793c5a34ec1c894580c52ffea5074b6ee0ee8e593d10ef12b40'
R20_MANIFEST_SHA = '98036d1133b0d93aa4c6e47d598ffd4a60d1f7021474f569c3a2ba24021e2b3b'
EXPECTED_COUNTS = {'IMMEDIATE':345893, 'ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF':310354}
EXPECTED_FILLS = {'IMMEDIATE':1963, 'ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF':1885}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def dumps(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def build(source: Path, contract: Path, out: Path) -> dict:
    encoder = CoreEncoder(contract)
    archive = None
    if source.is_file():
        with source.open('rb') as f:
            if hashlib.file_digest(f,'sha256').hexdigest() != R20_ZIP_SHA:
                raise ValueError('R20_ZIP_HASH')
        archive = zipfile.ZipFile(source)
    def read(name):
        return archive.read('run-a/'+name) if archive else (source/name).read_bytes()
    try:
        manifest_raw = read('manifest.json')
        if digest(manifest_raw) != R20_MANIFEST_SHA:
            raise ValueError('R20_MANIFEST_HASH')
        manifest = json.loads(manifest_raw)
        def pinned(name):
            raw = read(name)
            if digest(raw) != manifest[name]:
                raise ValueError('R20_MEMBER_HASH:'+name)
            return raw
        env_raw = pinned('entry-envelopes.json.gz')
        envelopes = json.loads(gzip.decompress(env_raw))
        if set(envelopes) != set(EXPECTED_COUNTS):
            raise ValueError('ENTRY_ARMS_DRIFT')
        entries = {}
        for arm, rows in envelopes.items():
            if len(rows)!=2155 or len({r['opportunity'] for r in rows})!=2155:
                raise ValueError('ENTRY_POPULATION_DRIFT')
            filled = [r for r in rows if r['entryId'] is not None]
            if len(filled)!=EXPECTED_FILLS[arm]:
                raise ValueError('ENTRY_FILL_DRIFT')
            entries.update({(arm,r['entryId']):r for r in filled})
        members = sorted(n for n in manifest if re.fullmatch(r'checkpoints/\d{4}-\d{2}-\d{2}\.jsonl\.gz',n))
        if len(members)!=58:
            raise ValueError('SESSION_COUNT_DRIFT')
        out.mkdir(parents=True,exist_ok=False)
        (out/'checkpoints').mkdir()
        (out/'entry-envelopes.json.gz').write_bytes(env_raw)
        header = {'schema':'phase57-r35-unscaled-core-columns-v1',
                  'categorical':encoder.categorical_names,'numeric':encoder.numeric_names,
                  'identityIsNotAFeature':True,'labelsIncluded':False,'preprocessingFitted':False}
        (out/'columns.json').write_bytes(dumps(header))
        counts = collections.Counter();last={};projection=hashlib.sha256()
        output_hashes = {'entry-envelopes.json.gz':digest(env_raw), 'columns.json':digest(dumps(header))}
        for member in members:
            compressed = pinned(member)
            target=out/member
            with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as inp, target.open('wb') as dst:
                with gzip.GzipFile(fileobj=dst,mode='wb',filename='',mtime=0,compresslevel=6) as output:
                    for line in inp:
                        row=json.loads(line)
                        key=(row['entryPolicy'],row['entry']['entryId'])
                        if key not in entries or row['entry']!=entries[key]:
                            raise ValueError('FROZEN_ENTRY_ENVELOPE_DRIFT')
                        if row['now']<=last.get(key,-1):
                            raise ValueError('DUPLICATE_OR_REVERSED_CHECKPOINT')
                        last[key]=row['now']
                        encoded=encoder.encode(row)
                        data=dumps(encoded);output.write(data);projection.update(data)
                        counts[key[0]]+=1
            output_hashes[member]=digest(target.read_bytes())
            print(member,dict(counts),flush=True)
        if dict(counts)!=EXPECTED_COUNTS or set(last)!=set(entries):
            raise ValueError('MISSING_CHECKPOINTS_OR_FILLED_ENTRIES')
        receipt={'schema':'phase57-r35-core-cache-receipt-v1','status':'COMPLETE_UNSCALED_CORE_CACHE_NOT_MODEL_RESULT',
                 'r20ManifestSha256':R20_MANIFEST_SHA,'fitContractSha256':digest(contract.read_bytes()),
                 'populationPerArm':2155,'filledEntries':EXPECTED_FILLS,'sessions':58,
                 'checkpointCounts':dict(counts),'categoricalFields':len(encoder.categorical_names),
                 'numericFields':len(encoder.numeric_names),'projectionSha256':projection.hexdigest(),
                 'outputHashes':output_hashes,'modelFits':0,'candidateReplays':0,'performanceInspections':0,
                 'providerRequests':0,'protectedPartitionsOpened':0,
                 'sourceHashes':{p.name:digest(p.read_bytes()) for p in (
                     Path(__file__),Path(__file__).with_name('phase57_exit_core_runtime_r35.py'))},
                 'safety':encoder.contract['safety']}
        (out/'manifest.json').write_bytes(dumps(receipt))
        return receipt
    except Exception as exc:
        if out.is_dir() and not (out/'manifest.json').exists():
            (out/'FAILURE.json').write_bytes(dumps({'status':'FAILED_NOT_REUSABLE','error':str(exc)}))
        raise
    finally:
        if archive:archive.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--r20-source',type=Path,required=True,help='Pinned ZIP or extracted run-a directory')
    parser.add_argument('--fit-contract',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    a=parser.parse_args();build(a.r20_source,a.fit_contract,a.out)
