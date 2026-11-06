"""Stage only required historical source members; no provider or EXIT/model access."""
import argparse
import shutil
import zipfile
from pathlib import Path
from settings import HERE, INPUT, sha

PACKAGES = {
    'Ark_FIRST_ENTRY_V2_P1_Q70_OFFICIAL_FREEZE_20261003_PRIVATE.zip':
        '0ede654a0a730f78bebeb4fcec1c21503de80c7cb2950d205aaf87e7c79853b7',
    'Persistent_Uptrend_FIRST_ENTRY_v2_PRIVATE_20261003.zip':
        'c0024055e9afa19089318c0f2a281e3fe15d48e10945b752be48e9239235ac15',
}
MEMBERS = {
    'Ark_FIRST_ENTRY_V2_P1_Q70_OFFICIAL_FREEZE_20261003_PRIVATE.zip': {
        'P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz':
            'ark-terminal/research/persistent-watchlist-uptrend-first-entry-20261003-v2/'
            'CORRECTED_LINEAGE_FAST_FREEZE_20261003/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz',
    },
    'Persistent_Uptrend_FIRST_ENTRY_v2_PRIVATE_20261003.zip': {
        'base/features_numeric.npy':
            'ark-terminal/research/persistent-watchlist-uptrend-first-entry-20261003-v2/PRIVATE_INPUTS/features_numeric.npy',
        'base/STATE_FEATURE_METADATA.jsonl.gz':
            'ark-terminal/research/persistent-watchlist-uptrend-first-entry-20261003-v2/STATE_FEATURE_METADATA.jsonl.gz',
        'base/raw_paths_selected.json.gz': 'persistent_sources/raw_paths_selected.json.gz',
        'base/PRIVATE_SELECTED_SOURCE_TOKENS.json.gz': 'private_source/PRIVATE_SELECTED_SOURCE_TOKENS.json.gz',
    },
}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packages', type=Path, default=INPUT/'library_sources')
    args = parser.parse_args()
    canonical_packages = INPUT/'library_sources'
    canonical_packages.mkdir(parents=True, exist_ok=True)
    for name, digest in PACKAGES.items():
        original = (args.packages/name).resolve()
        if sha(original) != digest:
            raise SystemExit('BLOCKED_STATE9_SOURCE_NOT_RECONSTRUCTIBLE: package hash '+name)
        canonical = canonical_packages/name
        if original != canonical.resolve() and not canonical.exists():
            try:
                canonical.symlink_to(original)
            except OSError:
                shutil.copyfile(original, canonical)
        if sha(canonical) != digest:
            raise SystemExit('BLOCKED_STATE9_SOURCE_NOT_RECONSTRUCTIBLE: canonical package '+name)
        with zipfile.ZipFile(original) as archive:
            for target, member in MEMBERS[name].items():
                dest = INPUT/target
                dest.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, dest.open('wb') as out:
                    shutil.copyfileobj(source, out)
    frozen = HERE/'FROZEN_SOURCE'
    for child in frozen.iterdir():
        if child.name == 'independent':
            dest = INPUT/'rc2_audit_source/reference/source/rc2/independent'
            shutil.copytree(child, dest, dirs_exist_ok=True)
        elif child.is_dir():
            shutil.copytree(child, INPUT/'rc2_kernel'/child.name, dirs_exist_ok=True)
        else:
            for dest in [INPUT/'rc2_kernel'/child.name, INPUT/'frozen'/child.name]:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(child, dest)
    shutil.copyfile(HERE/'FROZEN_ENTRY_IO_CONTRACT.json', INPUT/'P1_Q70_ENTRY_CONTRACT.json')
    assert sha(INPUT/'P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz') == 'e7a6140b6b11d8d078a271fad76b75e68a5b2fda9e45c7db43d98ee2f282abeb'
    print('Historical source and byte-identical Frozen RC2/Path staged; no models or old EXIT members opened.')

if __name__ == '__main__':
    main()
