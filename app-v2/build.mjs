import fs from 'node:fs';
fs.mkdirSync('dist',{recursive:true});for(const f of ['index.html','style.css'])fs.copyFileSync('public/'+f,'dist/'+f);
