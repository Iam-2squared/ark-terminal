from pathlib import Path
import json,zipfile,hashlib,base64
R=Path(__file__).resolve().parent
with zipfile.ZipFile(R/'COMPLETION_SOURCE.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in sorted((R/'runner').rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts:z.write(p,str(p.relative_to(R/'runner')))
b=(R/'COMPLETION_SOURCE.zip').read_bytes();h=hashlib.sha256(b).hexdigest()
(R/'payload.b64').write_text(base64.b64encode(b).decode())
template=(R/'INHERITED_WORKFLOW.yml').read_text()
template=template.replace('State NextState V2 Development Export','State Reversal V3 Fixed Development Completion').replace('state-predictiveness-v2-nextstate-20261002-v1','state-predictiveness-v3-reversal-20261002-v1').replace('state-nextstate-v2-20261002','state-reversal-v3-20261002').replace('state-nextstate-v2','state-reversal-v3').replace('export_expansion.py','export_completion.py').replace('7921e16634119d56bd4e24c3e8d369fda673d3f90759721e075dda7e1be8e50e',h)
template=template.replace('          GH_TOKEN: ${{ github.token }}\n','')
(R/'WORKFLOW.yml').write_text(template)
(R/'COMPLETION_SOURCE_RECEIPT.json').write_text(json.dumps({'SHA256':h,'bytes':len(b),'secret_values':0,'future_labels':0,'fanout':1},indent=2)+'\n')
print(json.dumps({'SHA256':h,'bytes':len(b),'base64_bytes':(R/'payload.b64').stat().st_size}))
