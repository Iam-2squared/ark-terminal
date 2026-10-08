async function publish_exact(stage) {
 const root='/workspace/scratch/85f3d8e4352b/rd02/';
 const cwd='/workspace/scratch/85f3d8e4352b';
 const sq=s=>"'"+s.replaceAll("'","'\\''")+"'";
 const command=async cmd=>{const r=await tools.exec_command({cmd,workdir:cwd,max_output_tokens:500000});if(r.exit_code!==0)throw Error(r.output);return r.output;};
 const put=async (path,x)=>{const b=JSON.stringify(x,null,2)+'\n';await tools.apply_patch('*** Begin Patch\n*** Add File: '+root+path+'\n'+b.split('\n').slice(0,-1).map(s=>'+'+s).join('\n')+'\n*** End Patch');};
  const utf8=s=>{const out=[];for(const c of s){const n=c.codePointAt(0);if(n<128)out.push(n);else if(n<2048)out.push(192|(n>>6),128|(n&63));else if(n<65536)out.push(224|(n>>12),128|((n>>6)&63),128|(n&63));else out.push(240|(n>>18),128|((n>>12)&63),128|((n>>6)&63),128|(n&63));}return new Uint8Array(out);};
  const unbase=s=>{s=s.replace(/\s/g,'');const abc='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/',o=[];for(let i=0;i<s.length;i+=4){const n=(abc.indexOf(s[i])<<18)|(abc.indexOf(s[i+1])<<12)|((s[i+2]==='='?0:abc.indexOf(s[i+2]))<<6)|(s[i+3]==='='?0:abc.indexOf(s[i+3]));o.push((n>>16)&255);if(s[i+2]!=='=')o.push((n>>8)&255);if(s[i+3]!=='=')o.push(n&255);}return new Uint8Array(o);};
  function digest(b){
    const K=[0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
    const H=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19],len=b.length,n=Math.ceil((len+9)/64)*64,buf=new Uint8Array(n);buf.set(b);buf[len]=128;const bits=len*8;for(let i=0;i<8;i++)buf[n-1-i]=Math.floor(bits/2**(8*i))&255;
    const r=(x,n)=>(x>>>n)|(x<<(32-n));
    for(let i=0;i<n;i+=64){const w=new Int32Array(64);for(let j=0;j<16;j++){const k=i+j*4;w[j]=(buf[k]<<24)|(buf[k+1]<<16)|(buf[k+2]<<8)|buf[k+3];}for(let j=16;j<64;j++){const a=w[j-15],c=w[j-2];w[j]=(w[j-16]+(r(a,7)^r(a,18)^(a>>>3))+w[j-7]+(r(c,17)^r(c,19)^(c>>>10)))|0;}
      let [a,c,d,e,f,g,h,j]=H;for(let k=0;k<64;k++){const t1=(j+(r(f,6)^r(f,11)^r(f,25))+((f&g)^(~f&h))+K[k]+w[k])|0,t2=((r(a,2)^r(a,13)^r(a,22))+((a&c)^(a&d)^(c&d)))|0;j=h;h=g;g=f;f=(e+t1)|0;e=d;d=c;c=a;a=(t1+t2)|0;}[a,c,d,e,f,g,h,j].forEach((x,k)=>H[k]=(H[k]+x)|0);
    }return H.map(x=>(x>>>0).toString(16).padStart(8,'0')).join('');
  }

 const assets=JSON.parse(await command('python -c '+sq("import json; x=json.load(open('rd02/transport/"+stage+"/assets.json')); [r.pop('content',None) for k in ['public','private'] for r in x[k]]; print(json.dumps(x,ensure_ascii=False))")));
 let state=JSON.parse(await command('cat rd02/transport/GITHUB_STATE.json'));
 let done=JSON.parse(await command('python -c '+sq("import pathlib; p=pathlib.Path('rd02/transport/"+stage+"/UPLOAD_STATE.json'); print(p.read_text() if p.exists() else '{}')")));
 const receipts=[];
 for(const [which,repo] of [['private','Iam-2squared/ark-capital-private-'],['public','Iam-2squared/ark-terminal']]){
  const aa=assets[which];if(!aa.length)continue;let head=done[which+'_head'];
  if(!head){const entries=[];
   for(let i=0;i<aa.length;i++){const q=aa[i],saved=JSON.parse(await command('python -c '+sq("import pathlib; p=pathlib.Path('rd02/transport/"+stage+"/EXACT_"+which+"_"+i+".json'); print(p.read_text() if p.exists() else '{}')")));
    if(saved.sha!==q.git_blob){const content=await command('python -c '+sq("import pathlib,base64,sys; b=pathlib.Path("+JSON.stringify(q.local)+").read_bytes(); sys.stdout.write(base64.b64encode(b).decode() if "+JSON.stringify(q.encoding)+"=='base64' else b.decode())"));
      const b=q.encoding==='base64'?unbase(content):utf8(content);if(b.length!==q.bytes||digest(b)!==q.sha256)throw Error('LOCAL_BEFORE_UPLOAD_HASH_DIFF:'+q.path);
      const z=await tools.mcp__codex_apps__github_create_blob({repository_full_name:repo,content,encoding:q.encoding});if(z.isError||z.structuredContent.sha!==q.git_blob)throw Error('UPLOAD_BLOB_HASH_DIFF:'+q.path);
      await put('transport/'+stage+'/EXACT_'+which+'_'+i+'.json',{sha:q.git_blob,path:q.path});
    }
    entries.push({path:q.path,mode:'100644',type:'blob',sha:q.git_blob});
   }
   const actual=await tools.mcp__codex_apps__github_fetch({url:'https://api.github.com/repos/'+repo+'/git/ref/heads/research/downside-direct-rd02-20261008'});if(actual.isError||JSON.parse(actual.structuredContent.content).object.sha!==state[which+'_head'])throw Error('BRANCH_HEAD_CHANGED_BEFORE_COMMIT:'+repo);
   const tree=await tools.mcp__codex_apps__github_create_tree({repository_full_name:repo,base_tree_sha:state[which+'_tree'],tree_elements:entries});if(tree.isError)throw Error(JSON.stringify(tree));
   const commit=await tools.mcp__codex_apps__github_create_commit({repository_full_name:repo,tree_sha:tree.structuredContent.sha,parent_sha:state[which+'_head'],message:'RD02 '+stage+' sealed offline research results'});if(commit.isError)throw Error(JSON.stringify(commit));
   const update=await tools.mcp__codex_apps__github_update_ref({repository_full_name:repo,branch_name:'research/downside-direct-rd02-20261008',sha:commit.structuredContent.sha,expected_sha:state[which+'_head'],force:false});if(update.isError)throw Error(JSON.stringify(update));
   head=commit.structuredContent.sha;state[which+'_head']=head;state[which+'_tree']=tree.structuredContent.sha;done[which+'_head']=head;done[which+'_tree']=tree.structuredContent.sha;await put('transport/GITHUB_STATE.json',state);await put('transport/'+stage+'/UPLOAD_STATE.json',done);
  }
  for(let i=0;i<aa.length;i+=4){const batch=aa.slice(i,i+4);const rr=await Promise.allSettled(batch.map(q=>tools.mcp__codex_apps__github_fetch_file({repository_full_name:repo,path:q.path,ref:head,encoding:q.encoding})));
    for(let j=0;j<rr.length;j++){const q=batch[j],v=rr[j];if(v.status!=='fulfilled'||v.value.isError)throw Error('ACTUAL_GET_FAILED:'+q.path);const payload=v.value.structuredContent,b=q.encoding==='base64'?unbase(payload.content):utf8(payload.content);if(payload.sha!==q.git_blob||b.length!==q.bytes||digest(b)!==q.sha256)throw Error('ACTUAL_GET_HASH_DIFF:'+q.path);receipts.push({repo,commit:head,path:q.path,bytes:b.length,sha256:q.sha256,git_blob:payload.sha,actual_GET:true,exact_bytes_and_hash_equal:true,stage});}
    await put('transport/'+stage+'/READBACK_PROGRESS.json',{stage,rows:receipts});
  }
  text({stage,repo,commit:head,files:aa.length,actual_GET:'PASS'});
 }
 await put('transport/'+stage+'/READBACK.json',{stage,public_commit:state.public_head,private_commit:state.private_head,rows:receipts});await command('python rd02/implementation/transport.py done '+stage);return receipts;
}
