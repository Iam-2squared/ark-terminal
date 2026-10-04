// Connector-only append publisher; persistence survives orchestration host resets.
store('r1Collect', (async function () {
  const old = load('r1Published');
  const src = `from pathlib import Path\nimport json,sys\nroot=Path('/workspace/scratch/d7576958b438/ark-terminal')\nold=set(json.loads(${JSON.stringify(JSON.stringify(old))}))\nfiles=[p for d in ('docs/evidence/capital-v8r1-cash-constrained-online-max3-20261005-v1','research/capital-v8r1-cash-constrained-online-max3-20261005-v1') for p in (root/d).rglob('*') if p.is_file() and '__pycache__' not in p.parts and (str(p.relative_to(root)) not in old or p.name=='WORK_STATUS_LOG.jsonl')]\ns=json.dumps([{'path':str(p.relative_to(root)),'mode':'100644','type':'blob','content':p.read_text()} for p in sorted(files)],ensure_ascii=False)\nstart=int(sys.argv[1]);print(len(s) if start<0 else s[start:start+24000])`;
  async function part(offset) {
    const r = await tools.exec_command({cmd:`python3 - ${offset} <<'PY'\n${src}\nPY`, max_output_tokens:15000});
    if (r.exit_code !== 0 || r.original_token_count>14500) throw Error('COLLECT_'+offset);
    return r.output.slice(0,-1);
  }
  const n = Number(await part(-1)); let chunks = [];
  // Bounded concurrency avoids an orchestration-host memory spike.
  for (let i=0; i<n; i+=48000) chunks.push(...await Promise.all([part(i), ...(i+24000<n?[part(i+24000)]:[])]));
  const all = JSON.parse(chunks.join('')).filter(x=>!x.path.endsWith('/WORK_STATUS_LOG.jsonl')||x.content!==load('r1Log'));
  text({new_files:all.length,chars:all.reduce((v,x)=>v+x.content.length,0)}); return all;
}).toString());
store('r1Publish', (async function (label, elements) {
  const repo='Iam-2squared/ark-terminal', branch='capital-v8r1-cashfix-20261005';
  function sc(r) { if(r.isError)throw Error(JSON.stringify(r)); return r.structuredContent; }
  const before=JSON.parse(sc(await tools.mcp__codex_apps__github_fetch({url:`https://api.github.com/repos/${repo}/branches/${branch}`})).content);
  const head=before.commit.sha, tree=before.commit.commit.tree.sha;
  if(head!==load('r1Head')||tree!==load('r1Tree'))throw Error('LATEST_MOVED_STOP');
  for(const x of elements)if(!/^(docs\/evidence|research)\/capital-v8r1-cash-constrained-online-max3-20261005-v1\//.test(x.path)||(load('r1Published').includes(x.path)&&!x.path.endsWith('/WORK_STATUS_LOG.jsonl'))||(x.path.endsWith('/WORK_STATUS_LOG.jsonl')&&!x.content.startsWith(load('r1Log')||'')))throw Error('APPEND_ONLY_STOP');
  const els=[];
  for(const x of elements) {
    if(x.content.length>60000) { const b=sc(await tools.mcp__codex_apps__github_create_blob({repository_full_name:repo,content:x.content,encoding:'utf-8'})); els.push({path:x.path,mode:x.mode,type:x.type,sha:b.sha}); }
    else els.push(x);
  }
  const tr=sc(await tools.mcp__codex_apps__github_create_tree({repository_full_name:repo,base_tree_sha:tree,tree_elements:els}));
  const cm=sc(await tools.mcp__codex_apps__github_create_commit({repository_full_name:repo,parent_sha:head,tree_sha:tr.sha,message:`research(capital-r1): ${label}`}));
  const check=JSON.parse(sc(await tools.mcp__codex_apps__github_fetch({url:`https://api.github.com/repos/${repo}/git/ref/heads/${branch}`})).content);
  if(check.object.sha!==head)throw Error('CONCURRENT_UPDATE_STOP');
  sc(await tools.mcp__codex_apps__github_update_ref({repository_full_name:repo,branch_name:branch,sha:cm.sha,force:false}));
  const after=JSON.parse(sc(await tools.mcp__codex_apps__github_fetch({url:`https://api.github.com/repos/${repo}/branches/${branch}`})).content);
  if(after.commit.sha!==cm.sha||after.commit.commit.tree.sha!==tr.sha)throw Error('RECEIPT_MISMATCH_STOP');
  const time=new Date(Date.now()+9*3600000).toISOString().replace('Z','+09:00');
  const receipt={checkpoint:label,exact_jst:time,basis_HEAD:head,basis_tree:tree,actual_HEAD:cm.sha,actual_tree:tr.sha,actual_GET_verified:true,force:false,paths:els.map(x=>x.path)};
  const bp='/workspace/scratch/d7576958b438/r1_work/latest_basis.json';
  const old=(await tools.exec_command({cmd:`sed -n '1,1p' ${bp}`,max_output_tokens:1000})).output.trim();
  const nb=JSON.stringify({HEAD:cm.sha,tree:tr.sha,exact_jst:time,actual_GET_verified:true});
  const rp=`/workspace/scratch/d7576958b438/ark-terminal/docs/evidence/capital-v8r1-cash-constrained-online-max3-20261005-v1/receipts/${label}_ACTUAL_GET.json`;
  await tools.apply_patch(`*** Begin Patch\n*** Add File: ${rp}\n${JSON.stringify(receipt,null,2).split('\n').map(x=>'+'+x).join('\n')}\n*** Update File: ${bp}\n@@\n-${old}\n+${nb}\n*** End Patch`);
  for(const x of elements)if(x.path.endsWith('/WORK_STATUS_LOG.jsonl'))store('r1Log',x.content);
  store('r1Head',cm.sha);store('r1Tree',tr.sha);store('r1Published',[...load('r1Published'),...els.map(x=>x.path)]);store('r1LastReceipt',receipt);
  text({checkpoint:label,actual_HEAD:cm.sha,actual_tree:tr.sha,exact_jst:time,file_N:els.length,actual_GET_verified:true});
}).toString());
