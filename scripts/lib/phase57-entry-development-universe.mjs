import assert from 'node:assert/strict';

// Preserve Admission's common-issue filter before the lossy display-symbol mapping.
export function developmentUniverse(source) {
 const byCode=new Map(), bySymbol=new Map();
 for(const m of source.master){
  assert(!byCode.has(m.sourceCode),'DUPLICATE_MASTER_CODE');byCode.set(m.sourceCode,m);
 }
 const bars=[];
 for(const b of source.bars){
  const m=byCode.get(b.sourceCode),common=b.sourceCode.length===4||b.sourceCode.endsWith('0');
  if(!m||!common||!['0111','0112','0113'].includes(m.marketCode)||m.productCategory!=='011')continue;
  assert.equal(b.symbol,m.symbol,'SOURCE_MASTER_SYMBOL_MISMATCH');
  const previous=bySymbol.get(b.symbol);
  assert(!previous||previous.sourceCode===b.sourceCode,'AMBIGUOUS_COMMON_ISSUE_SYMBOL');
  bySymbol.set(b.symbol,m);bars.push(b);
 }
 assert.deepEqual([...bySymbol.keys()].sort(),[...source.members].sort(),'ADMISSION_MEMBER_SET_MISMATCH');
 return {bars,meta:bySymbol};
}
