import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

test('No.1.1 offline 2025 research scorer blocks production and post-decision values',()=>{
 const filename=path.resolve('research/no12-prebuy-causal-runtime-20261011/tools/no11_asof_research_score_offline.py');
 const src=fs.readFileSync(filename,'utf8');
 assert.match(src,/OFFLINE_RESEARCH_ONLY/);
 assert.match(src,/orderTransmission/);
 assert.doesNotMatch(src,/RssStockOrder\s*\(|RssCancelOrder\s*\(|Excel\.Application|requests\.|urllib\.|socket\.|subprocess\./);
 const py="import hashlib,importlib.util,json,math,subprocess,sys,tempfile\nfrom pathlib import Path\nmname=Path(sys.argv[1])\nspec=importlib.util.spec_from_file_location('research_only',mname)\nm=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\nmodel={\n 'schemaId':m.MODEL_SCHEMA,'head':'H2',\n 'feature_input_asof':'BUY_INTENT_WITH_ASSUMED_BAR_AVAILABILITY',\n 'training_label':'LEGACY_POST_FILL_POTENTIAL_2025',\n 'trained_on_2026_rss_rows':0,'historical_actual_known_at':'UNKNOWN',\n 'frozen_no11_model_modified':False,'model_production_eligible':False,\n 'productionReady':False,'orderTransmission':False,\n 'preprocessing':{'numeric_fields':['n'],'categorical_fields':['cat'],\n  'numeric_mean':[0.,0.],'numeric_scale':[1.,1.],\n  'categorical_train_vocab':{'cat':['ON','__UNKNOWN__']}},\n 'coef':[1.,0.,0.2,-0.2],'intercept':0.\n}\nrow={'schemaId':m.FEATURE_SCHEMA,'mode':m.ALLOWED_MODE,\n 'featureTime':'BUY_INTENT','pointInTimeCertified':False,\n 'numeric':{'n':1.},'categorical':{'cat':'ON'},\n 'productionReady':False,'orderTransmission':False}\nprob=m.score(model,row)\nassert abs(prob-1/(1+math.exp(-1.2)))<1e-14,prob\nwith tempfile.TemporaryDirectory() as folder:\n p=Path(folder)\n (p/'m.json').write_text(json.dumps(model))\n (p/'x.json').write_text(json.dumps(row))\n done=subprocess.run([sys.executable,'-B',str(mname),\n    '--mode','OFFLINE_RESEARCH_ONLY','--model',str(p/'m.json'),\n    '--features',str(p/'x.json'),'--output',str(p/'out.json')],\n    capture_output=True,text=True,timeout=30)\n assert done.returncode==0,done.stderr\n assert 'ORDER_TRANSMISSION=False' in done.stdout\n assert json.loads((p/'out.json').read_text())['productionReady'] is False\n unsafe={**model,'productionReady':True}\n try:m.score(unsafe,row)\n except ValueError as e:assert 'UNAPPROVED' in str(e)\n else:raise AssertionError('unsafe model allowed')\n future={**row,'future_high':100}\n try:m.score(model,future)\n except ValueError:pass\n else:raise AssertionError('future field allowed')\n unknown={**row,'numeric':{'n':None}}\n assert math.isfinite(m.score(model,unknown))\nprint('NO11_ASOF_SCORE_OFFLINE_SYNTHETIC=PASS')\n";
 const exe=process.platform==='win32'?'python':'python3';
 const p=spawnSync(exe,['-B','-c',py,filename],{encoding:'utf8',timeout:60000});
 assert.equal(p.status,0,'Python offline research scorer failed: '+String(p.stderr||p.error||p.stdout));
 assert.match(p.stdout,/NO11_ASOF_SCORE_OFFLINE_SYNTHETIC=PASS/);
});
