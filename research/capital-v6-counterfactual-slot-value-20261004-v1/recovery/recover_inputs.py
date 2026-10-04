"""Reuse a strict allowlist of archived bytes against GitHub's D1 freeze."""
import io, json, zipfile
from pathlib import Path
from control import WORK, OUT, now, save, sha

def main():
    expected = json.loads((OUT / 'SOURCE_HASHES.json').read_text())
    archive = WORK / 'project_sources/20-Ark_Capital_v4_Rank_Cutoff_Independent_20261004_PRIVATE.zip'
    nested = 'deliverables/Ark_Capital_MAX3_Upward_Staircase_v4_20261004_PRIVATE.zip'
    names = [
        'capital_staircase_v4_private/UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz',
        'capital_staircase_v4_private/MODEL_HASHES.json',
        'inputs/v3/bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz',
        'inputs/v3/capital_v2_private/TEACHERS_EVALUATION.jsonl.gz',
        'repo/docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json',
    ] + [f'capital_staircase_v4_private/models/H{h}_BLOCK_{b:02d}.json'
         for h in (2, 3, 5) for b in range(1, 9)]
    import hashlib
    checks = []
    with zipfile.ZipFile(archive) as outer:
        with zipfile.ZipFile(io.BytesIO(outer.read(nested))) as source:
            for name in names:
                key = 'source_main/' + name
                data = source.read(name)
                actual = hashlib.sha256(data).hexdigest()
                if actual != expected[key]:
                    raise RuntimeError(('RECOVERY_HASH_MISMATCH', key, actual, expected[key]))
                dest = WORK / key
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open('xb') as f:
                    f.write(data)
                checks.append({'path': key, 'sha256': actual, 'matched': True})
    models = json.loads((OUT / 'SLOT_FITS_FREEZE.json').read_text())['models']
    private = WORK / 'capital_v6_slot_private'
    private.mkdir(exist_ok=True)
    for b, digest in models.items():
        original = OUT / 'models' / f'SLOT_MODEL_BLOCK_{int(b):02d}.json'
        assert sha(original) == digest, 'RECOVERY_HASH_MISMATCH'
        with (private / original.name).open('xb') as f:
            f.write(original.read_bytes())
    save(OUT / 'RECOVERY_INPUT_IDENTITY.json', {
        'exact_jst': now(), 'recovery_state_authority': 'GitHub append-only Evidence at latest HEAD',
        'input_transport': 'Existing attached v4 archive, nested original; SHA256 pinned in GitHub D1 SOURCE_HASHES',
        'checks': checks, 'mismatch_N': 0, 'model_copy_N': 8,
        'teacher_regeneration': 0, 'fits': 0, 'replays': 0,
        'protected_holdout_fresh_validation_OOS_prospective_opened': 0,
        'archive_read_allowlist_only': True,
    })
    print(json.dumps({'input_checks': len(checks), 'mismatch_N': 0, 'model_copies': 8, 'exact_jst': now()}))

if __name__ == '__main__':
    main()
