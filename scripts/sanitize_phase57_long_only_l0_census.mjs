import fs from 'node:fs';
import path from 'node:path';

const arg=name=>{const index=process.argv.indexOf(name);return index<0?null:process.argv[index+1];};
const input=arg('--input'),output=arg('--output');
if(!input||!output)throw new Error('usage: --input <formal-census.json> --output <sanitized-census.json>');

const census=JSON.parse(fs.readFileSync(input,'utf8'));
if(census?.status!=='LONG_ONLY_L0_CENSUS_READY')throw new Error('input is not a Formal L0 census');
const exclusions=Array.isArray(census?.admissionAudit?.exclusions)?census.admissionAudit.exclusions:[];
const sanitized={
  ...census,
  admissionAudit:{
    ...census.admissionAudit,
    exclusions:undefined,
    exclusionIdentitiesPublished:false,
    exclusionIdentityCount:exclusions.length,
  },
};
fs.mkdirSync(path.dirname(output),{recursive:true});
fs.writeFileSync(output,`${JSON.stringify(sanitized,null,2)}\n`,{flag:'wx'});
console.log(JSON.stringify({status:'SANITIZED_L0_CENSUS_READY',partition:census.partition,sessionCount:census.lineage?.sessionCount,exclusionIdentityCount:exclusions.length,output}));
