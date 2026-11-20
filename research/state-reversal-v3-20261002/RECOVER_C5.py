"""Restore a truncated JSONL from its complete CSV exports; never fit or draw."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv, json, hashlib, os
R = Path(__file__).resolve().parent
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    expected = json.loads((R/'C5_OOF_FIXATION_RECEIPT.json').read_text())
    original = R/'OOF_ALL.jsonl'
    if sha(original) == expected['OOF_SHA256']:
        print('OOF_ALREADY_EXACT'); return
    rows = []
    for task in json.loads((R/'REVERSAL_TARGET_SCHEMA.json').read_text())['classes']:
        with (R/(task+'_OOF_PREDICTIONS.csv')).open() as stream:
            for row in csv.DictReader(stream):
                row['probabilities'] = json.loads(row['probabilities'])
                row['fold'] = int(row['fold'])
                row['calibrated'] = row['calibrated'] == 'True'
                rows.append(row)
    encoded = ''.join(json.dumps(row, sort_keys=True, separators=(',',':'))+'\n' for row in rows).encode()
    assert len(rows) == expected['classification_records']
    assert hashlib.sha256(encoded).hexdigest() == expected['OOF_SHA256'], 'NOT_EXACT_ORIGINAL_BYTES'
    before_rows = list(map(json.loads, original.read_text().splitlines()))
    assert before_rows == rows[:len(before_rows)], 'TRUNCATION_NOT_EXACT_PREFIX'
    receipt = {'JST': datetime.now(timezone(timedelta(hours=9))).isoformat(),
        'finding': 'JSONL_WAS_EXACT_TRUNCATED_PREFIX_COMPLETE_CSV_EXPORTS_RETAINED',
        'prefix_rows': len(before_rows), 'original_receipt_rows': len(rows),
        'prefix_SHA256': sha(original), 'restored_SHA256': expected['OOF_SHA256'],
        'byte_identical_to_original_C5_receipt': True, 'refits': 0, 'new_draws': 0,
        'source_CSVs': {task+'_OOF_PREDICTIONS.csv': sha(R/(task+'_OOF_PREDICTIONS.csv'))
            for task in json.loads((R/'REVERSAL_TARGET_SCHEMA.json').read_text())['classes']}}
    findings = R/'RECOVERY_FINDINGS'; findings.mkdir(exist_ok=True)
    preserved = findings/'OOF_ALL_TRUNCATED.jsonl'
    assert not preserved.exists()
    original.rename(preserved)
    temporary = R/'OOF_ALL.jsonl.tmp'
    with temporary.open('wb') as stream:
        stream.write(encoded); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, original)
    (R/'C5_RESTORE_RECEIPT.json').write_text(json.dumps(receipt, sort_keys=True, indent=2)+'\n')
    print(json.dumps(receipt))
if __name__ == '__main__': main()
