from pathlib import Path
import json,hashlib,zipfile,base64,ast
R=Path(__file__).resolve().parent;T=R/'runner';P=Path('/workspace/scratch/a1e749e0bd6c/state_predictiveness_v3_reversal_20261002_v1')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
src=(P/'runner/export_completion.py').read_text()
src=src.replace('from CAUSAL_FEATURE_BUILDER import FeatureBuilder','from CAUSAL_FEATURE_BUILDER import FeatureBuilder\nfrom metadata_universe import build as metadata_build')
src=src.replace("pre=json.loads((H/'ACQUISITION_COMPLETION_PRECOMMIT.json').read_text())","pre=json.loads((H/'ACQUISITION_EXPANSION_PRECOMMIT.json').read_text())")
src=src.replace("proposals=pre['proposals'];allowed=", "universe=metadata_build(H,save);proposals=universe['proposals'];allowed=")
src=src.replace("assert pre['pending_ordinals']==list(range(40,73)),'ORIGINAL_SELECTION_ORDER'", "assert len(proposals)<=318,'PROPOSAL_CAP'")
src=src.replace("save('ACQUISITION_COMPLETION_PRECOMMIT.json',pre)","save('ACQUISITION_EXPANSION_PRECOMMIT.json',pre)")
src=src.replace('provider_stopped=None',"provider_stopped=universe['provider_stopped']")
src=src.replace("for k in pre['pending_ordinals']:","for k in range(1,len(proposals)+1):")
src=src.replace("pid=f'N{k:03d}'", "pid=f'V4N{k:03d}'")
src=src.replace("assert steps<=18000,'KERNEL_CAP'", "assert steps<=110000,'KERNEL_CAP'")
src=src.replace('FROZEN_CURRENT_SLOT_GENERATION_V3','FROZEN_CURRENT_SLOT_GENERATION_V4')
src=src.replace("'fixed_pending_proposals':33", "'fixed_pending_proposals':len(proposals) if 'proposals' in globals() else 0,'fixed_date_links':106")
src=src.replace('state-reversal-v3-raw','state-reversal-v4-raw')
(T/'export_expansion_v4.py').write_text(src)
for p in T.rglob('*.py'):ast.parse(p.read_text())
payload=R/'ACQUISITION_PAYLOAD_V4.zip'
with zipfile.ZipFile(payload,'x',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(T.rglob('*')):
  if p.is_file() and '__pycache__' not in str(p):z.write(p,str(p.relative_to(T)))
(R/'ACQUISITION_PAYLOAD_V4.b64').write_text(base64.b64encode(payload.read_bytes()).decode()+'\n')
workflow='''name: State Predictiveness V4 Fixed Development Expansion
on:
  push:
    branches: [state-predictiveness-v4-confirmation-20261002-v1]
    paths: ['.github/workflows/state-confirmation-v4-20261002.yml', 'research/state-confirmation-v4-20261002/payload.b64']
permissions:
  contents: read
concurrency:
  group: state-confirmation-v4-20261002
  cancel-in-progress: false
jobs:
  development-export:
    if: github.ref == 'refs/heads/state-predictiveness-v4-confirmation-20261002-v1'
    runs-on: ubuntu-latest
    timeout-minutes: 90
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      - name: Verify fixed source and scope
        run: |
          python - <<'PY'
          import pathlib,os,zipfile,base64,io,hashlib
          b=base64.b64decode(pathlib.Path('research/state-confirmation-v4-20261002/payload.b64').read_bytes())
          assert hashlib.sha256(b).hexdigest()=='PAYLOAD_HASH'
          with zipfile.ZipFile(io.BytesIO(b)) as z:
              assert all(not n.startswith('/') and '..' not in pathlib.PurePosixPath(n).parts for n in z.namelist())
              z.extractall(pathlib.Path(os.environ['RUNNER_TEMP'])/'state-reversal-v4-code')
          PY
      - name: Fixed approved Development metadata then temporary raw current-slot export
        env:
          JQUANTS_API_KEY: ${{ secrets.JQUANTS_API_KEY }}
          STATE9_AUDIT_RAW: ${{ runner.temp }}/state-reversal-v4-raw
          STATE9_AUDIT_OUT: ${{ runner.temp }}/state-reversal-v4-evidence
        run: python "$RUNNER_TEMP/state-reversal-v4-code/export_expansion_v4.py"
      - name: Purge exact temporary directory
        if: always()
        run: |
          python - <<'PY'
          import pathlib,os,shutil,json
          raw=pathlib.Path(os.environ['RUNNER_TEMP'])/'state-reversal-v4-raw'
          if raw.exists():shutil.rmtree(raw)
          out=pathlib.Path(os.environ['RUNNER_TEMP'])/'state-reversal-v4-evidence';out.mkdir(exist_ok=True)
          (out/'WORKFLOW_PURGE_RECEIPT.json').write_text(json.dumps({'verified':not raw.exists(),'secret_export':0})+'\\n')
          PY
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: state-predictiveness-v4-development-${{ github.run_id }}
          path: ${{ runner.temp }}/state-reversal-v4-evidence
          retention-days: 7
'''.replace('PAYLOAD_HASH',sha(payload))
(R/'state-confirmation-v4-20261002.yml').write_text(workflow)
(R/'WORKFLOW_PREFLIGHT_V4.json').write_text(json.dumps({'fanout':1,'dedicated_branch':'state-predictiveness-v4-confirmation-20261002-v1','only_new_workflow':True,'existing_workflows_changed':0,'no_PR':True,'payload_SHA256':sha(payload),'source_export_SHA256':sha(T/'export_expansion_v4.py'),'metadata_source_SHA256':sha(T/'metadata_universe.py'),'old88workflow_incident_retained':True},indent=2)+'\n')
print(json.dumps({'payload_bytes':payload.stat().st_size,'payload_SHA256':sha(payload),'source_files':len(z.namelist())}))
