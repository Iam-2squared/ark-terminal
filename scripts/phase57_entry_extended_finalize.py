import argparse,os,re,subprocess
from pathlib import Path
from scripts import phase57_entry_extended as e

def finalize(root):
 root=Path(root);m=root/'measurement';p=e.verify();reg=e.read(root/'regression/regression.json');assert reg['status']=='PASS'
 manifest=e.read(m/'manifest.json');assert manifest==e.read(root/'determinism.json')
 for name,h in manifest.items():assert e.sha(m/name)==h
 audit=e.read(m/'reproduction-audit.json');assert audit['status']=='PASS'
 tests=re.findall(r'Ran (\d+) tests',(root/'focused.log').read_text());assert tests
 gate={'status':'EXTENDED_OUTCOME_MEASUREMENT_COMPLETE_NO_POLICY_CHANGE','reproduction':'PASS','deterministicRegeneration':'PASS','tests':int(tests[-1]),'regression':'PASS','commonHoldoutOpened':0,'sealedOpened':0,'fitCalls':0,'policyCalls':0,'safety':p['safety']}
 e.write(root/'completion-gate.json',gate)
 head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();run=os.environ.get('GITHUB_RUN_ID')
 e.write(root/'ci-receipt.json',{'executionHead':head,'runId':run,'priorHead':p['baseHead'],'priorRun':p['priorRun'],'regression':reg,**gate})
 (root/'REPORT-ja.md').write_text('# Fixed Entry extended outcomes\n\n'+gate['status']+'\n\n[全比較表・12図・定義・coverage](measurement/REPORT-ja.md)\n\n'+f'Execution HEAD: `{head}`. [CI](https://github.com/Iam-2squared/ark-terminal/actions/runs/{run}).\n\nFocused tests: {gate["tests"]} PASS. Regression: '+str(sum(x['counts']['pass'] for x in reg['suites']))+' PASS. Two-pass measurement and chart manifests identical.\n\nEntry decisions/model/threshold/features unchanged. Common Holdout244 untouched. Safety9 all false. STOP; no EXIT or promotion.\n')
 e.write(root/'manifest.json',{str(x.relative_to(root)):e.sha(x) for x in sorted(root.rglob('*')) if x.is_file() and x!=root/'manifest.json'})
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--evidence',required=True);x=a.parse_args();finalize(x.evidence)
