function hash(value){

return JSON.stringify(value);

}

export class AnalysisCache{

constructor(){

this.cache=new Map();

}

set(key,value){

this.cache.set(

hash(key),

{

time:Date.now(),

value

}

);

return value;

}

get(key,maxAgeMs=300000){

const item=

this.cache.get(

hash(key)

);

if(!item){

return null;

}

if(

Date.now()-item.time>

maxAgeMs

){

this.cache.delete(

hash(key)

);

return null;

}

return item.value;

}

has(key){

return this.get(key)!==null;

}

clear(){

this.cache.clear();

}

size(){

return this.cache.size;

}

}

export const

analysisCache=

new AnalysisCache();