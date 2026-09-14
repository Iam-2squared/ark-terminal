import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {assemble,sourceFromCapture} from './data.mjs';
import {demoStatus} from './demo.mjs';
const here=path.dirname(fileURLToPath(import.meta.url)),MAX=4*1024*1024;
export function readInput(file,tail=false){if(!file)return null;const stat=fs.lstatSync(file);if(!stat.isFile()||stat.isSymbolicLink())throw Error('REGULAR_FILE_REQUIRED');const fd=fs.openSync(file,'r');try{if(!tail&&stat.size>MAX)throw Error('SIZE_LIMIT');const size=Math.min(stat.size,MAX),buf=Buffer.alloc(size);const read=fs.readSync(fd,buf,0,size,stat.size-size),end=fs.fstatSync(fd);if(read!==size||end.size!==stat.size||end.mtimeMs!==stat.mtimeMs)throw Error('CHANGED_DURING_READ');let text=buf.toString('utf8');if(tail){if(stat.size>MAX){const i=text.indexOf('\n');if(i<0)throw Error('RECORD_SIZE_LIMIT');text=text.slice(i+1);}if(!text.endsWith('\n'))throw Error('PARTIAL_STATUS_WRITE');text=text.trim().split('\n').at(-1)??'';}return JSON.parse(text.replace(/^\uFEFF/,''));}finally{fs.closeSync(fd);}}
export function createServer(config={}){
 const system={};for(const [k,args]of [['head',['rev-parse','HEAD']],['branch',['branch','--show-current']]])try{system[k]=execFileSync('git',args,{cwd:here,encoding:'utf8'}).trim();}catch{system[k]='UNKNOWN';}
 let last=null;const history=[];
 return http.createServer((req,res)=>{
  res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'");
  const host=req.headers.host??'';if(!/^(127\.0\.0\.1|localhost)(:\d+)?$/.test(host)){res.writeHead(403);res.end('LOCAL_HOST_REQUIRED');return;}if(req.method!=='GET'){res.writeHead(405,{Allow:'GET'});res.end('READ_ONLY');return;}if(req.headers.origin&&req.headers.origin!==`http://${host}`){res.writeHead(403);res.end('SAME_ORIGIN_REQUIRED');return;}
  const url=new URL(req.url,'http://localhost');if(url.pathname==='/api/status'){
   let s;if(config.demo)s=demoStatus();else{let source=null,execution=null;const errors=[];for(const [key,file]of [['source',config.sourceCapturePath||config.sourceSummaryPath],['execution',config.executionSnapshotPath]])try{const d=readInput(file,key==='source'&&Boolean(config.sourceCapturePath));if(key==='source')source=config.sourceCapturePath&&d?sourceFromCapture(d):d;else execution=d;}catch(e){errors.push(`${key.toUpperCase()}_UNAVAILABLE: ${e.message}`);}s=assemble({source,execution,errors,system:{...system,workbookPath:config.workbookPath??'UNBOUND',evidencePath:config.sourceCapturePath??config.sourceSummaryPath??'UNBOUND'}});if(s.portfolio&&execution?.lastAt&&execution.lastAt!==last){if(last&&execution.lastAt<last)history.length=0;history.push({at:execution.lastAt,equity:s.portfolio.equity,pnl:s.portfolio.pnl,flow:s.portfolio.flow});if(history.length>5000)history.shift();last=execution.lastAt;}if(!s.portfolio){history.length=0;last=null;}s.history=[...history];}
   res.setHeader('Content-Type','application/json');res.end(JSON.stringify(s));return;}
  if(url.pathname==='/legacy'){res.setHeader('Content-Type','text/plain; charset=utf-8');res.end('旧UIは既存のURL・起動方法で引き続き利用できます。App v2は旧APIを公開しません。');return;}
  const assets={'/':'index.html','/app.js':'app.js','/contracts.js':'contracts.js','/style.css':'style.css'};if(!Object.hasOwn(assets,url.pathname)){res.writeHead(404);res.end('NOT_FOUND');return;}const name=assets[url.pathname];try{res.setHeader('Content-Type',name.endsWith('.html')?'text/html; charset=utf-8':name.endsWith('.css')?'text/css':'text/javascript');res.end(fs.readFileSync(path.join(here,'dist',name)));}catch{res.writeHead(503);res.end('APP_BUILD_REQUIRED');}
 });
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){const i=process.argv.indexOf('--config');const c=i>=0?readInput(path.resolve(process.argv[i+1])):{};c.demo=process.argv.includes('--demo');const server=createServer(c);server.listen(8767,'127.0.0.1',()=>console.log('Ark App v2: http://127.0.0.1:8767 (READ ONLY)'));for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>server.close(()=>process.exit(0)));}
