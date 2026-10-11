#!/usr/bin/env node
// Diagnostic only: do not move private models to GitHub or create live intents.
import path from 'node:path';
import {auditNo11FrozenModelSource} from '../runtime/native_model_source_audit.mjs';
function printSafe(x){
  console.log('NO11_NATIVE_MODEL_STATUS='+x.status);
  console.log('NO11_NATIVE_MODELS_VERIFIED='+x.verifiedModels+'/24');
  console.log('NO11_NATIVE_MODELS_MISSING='+x.missingModels);
  console.log('NO11_NATIVE_MODELS_CHANGED='+x.changedModels);
  console.log('NO11_NATIVE_MODELS_UNSAFE='+x.unsafeModels);
  console.log('NO11_NATIVE_DECISION_EMITTED=False');
  console.log('NO11_PRODUCTION_READY=False');
  console.log('ORDER_TRANSMISSION=False');
}
try{
  if(process.argv.length!==2||!process.env.LOCALAPPDATA)throw Error('PRIVATE_LOCAL_ROOT_REQUIRED');
  const modelRoot=path.join(process.env.LOCALAPPDATA,'ArkTerminal','No11','private-native-models');
  const result=auditNo11FrozenModelSource({modelRoot});
  printSafe(result);
}catch{
  console.log('NO11_NATIVE_MODEL_STATUS=BLOCKED_SOURCE_AUDIT');
  console.log('NO11_NATIVE_DECISION_EMITTED=False');
  console.log('NO11_PRODUCTION_READY=False');
  console.log('ORDER_TRANSMISSION=False');
  process.exitCode=2;
}
