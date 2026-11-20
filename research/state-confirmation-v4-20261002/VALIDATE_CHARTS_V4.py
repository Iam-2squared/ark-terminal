from pathlib import Path
import json,hashlib
from PIL import Image
R=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((R/'CHART_MANIFEST.json').read_text());checks=[]
assert m['unique_figures']==len(m['figures'])==12
for x in m['figures']:
 for n,h in x['source_CSVs'].items():assert sha(R/n)==h,('CHART_SOURCE_CHANGED',n)
 im=Image.open(R/x['PNG']);im.verify();im=Image.open(R/x['PNG']);assert im.width>=800 and im.height>=400,'CHART_SIZE'
 assert '<svg' in (R/x['SVG']).read_text(),'SVG_INVALID'
 checks.append({'figure':x['figure'],'PNG_SHA256':sha(R/x['PNG']),'SVG_SHA256':sha(R/x['SVG']),'width':im.width,'height':im.height,'source_hash_PASS':True})
(R/'CHART_VALIDATION_V4.json').write_text(json.dumps({'status':'PASS','unique_figures':12,'formats':['PNG','SVG'],'checks':checks,'visual_inspection':'Main risk, calibration and precision plots are inspected in the execution record; data validation uses saved CSVs.','new_fits':0,'new_draws':0},indent=2)+'\n')
print(json.dumps({'status':'PASS','unique_figures':12,'source_hashes':'PASS'}))
