#!/usr/bin/env node
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {digest,FREEZE,SAFETY} from './lib/phase57-offline-parity.mjs';
import {inspectOosPrecommit} from './lib/phase57-integration-gates.mjs';
const [paritySummary,output]=process.argv.slice(2);
if(!paritySummary||!output)throw Error('PARITY_SUMMARY_AND_NEW_OUTPUT_REQUIRED');
const summaryBytes=fs.readFileSync(paritySummary),parity=JSON.parse(summaryBytes);
const files=['scripts/lib/phase57-integration-gates.mjs','scripts/lib/phase57-source-observer.mjs','scripts/lib/phase57-operational-robustness.mjs','scripts/phase57-source-diagnostic.mjs','scripts/phase57-post-close-parity.mjs','scripts/tests/phase57-integration-gates.test.mjs','tools/phase57_source_capture.py','tools/test_phase57_source_capture.py','tools/phase57_generic_excel_reader.py','tools/Start-ArkParity.ps1','tools/phase57-source-capture.example.json','predict/research/phase57-offline-parity/real-source-contract.json'];
const result={schemaId:'ARK_FINAL_INTEGRATION_EVIDENCE_V1',baseHead:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),freezeSha256:FREEZE,
  files:Object.fromEntries(files.map(f=>[f,digest(fs.readFileSync(f))])),historicalSummaryHash:digest(summaryBytes),historicalParity:parity,
  oos:inspectOosPrecommit(process.cwd()),actualExcelTested:false,actualMsiiTested:false,sourceSemanticsVerified:false,realTimeShadowUnlocked:false,
  independentHistoricalSelectorParity:'NOT_MEASURED',independentHistoricalV4Parity:'NOT_MEASURED',safety:SAFETY};
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
