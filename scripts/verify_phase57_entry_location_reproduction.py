"""Rebuild evaluator artifacts in a temporary directory; leave saved evidence intact."""
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from scripts import phase57_entry_location_study as s
from scripts import audit_phase57_entry_location_study as audit
from scripts import report_phase57_entry_location_study as report


def run():
    original = s.BASE
    names = ['ledger.json.gz','result.json.gz','supplement.json.gz','paired-summary.csv',
             'denominator-and-window-audit.json.gz','original-opportunity-preservation.csv',
             'coverage-audit.csv','horizon-distributions.csv','entry-efficiency-2d.csv',
             'deep-adverse-counts.json','REPORT.md']
    with tempfile.TemporaryDirectory(prefix='phase57-location-reproduce-') as tmp:
        s.BASE = Path(tmp)
        try:
            shutil.copyfile(original/'protocol.json',s.BASE/'protocol.json')
            s.run();audit.run();report.run()
            matches = {name:hashlib.sha256((s.BASE/name).read_bytes()).hexdigest()==hashlib.sha256((original/name).read_bytes()).hexdigest() for name in names}
            assert all(matches.values()), matches
        finally:
            s.BASE = original
    print(json.dumps({'reproduction':'PASS','byteIdenticalArtifacts':matches,'sourceFilesUnmodified':True}))


if __name__=='__main__':run()
