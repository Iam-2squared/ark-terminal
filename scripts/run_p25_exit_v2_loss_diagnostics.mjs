#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {diagnoseP25ExitV2VsFixedPairs,P25_EXIT_V2_LOSS_DIAGNOSTIC_SAFETY} from '../predict/daytrade/phase57-p25-exit-v2-loss-diagnostics.js';
const arg=n=>{const i=process.argv.indexOf(n);return i>=0?process.argv[i+1]:null;};
const input=arg('--input'),out=arg('--out'),sourceRunId=arg('--source-run-id'),sourceArtifact=arg('--source-artifact'),sourceDigest=arg('--source-digest');
if(!input||!out)throw new Error('usage: node scripts/run_p25_exit_v2_loss_diagnostics.mjs --input <combined-replay.json> --out <diagnostic.json> [--source-run-id ... --source-artifact ... --source-digest ...]');
const raw=JSON.parse(fs.readFileSync(input,'utf8'));const replay=raw?.result??raw;const pairs=replay?.pairs;if(!Array.isArray(pairs))throw new Error('P25 EXIT v2 loss diagnostic: replay pairs missing');
if(replay?.methodology?.formalOosEvidence!==false||replay?.methodology?.promotionEligible!==false||replay?.methodology?.freshHoldoutConsumed!==false)throw new Error('P25 EXIT v2 loss diagnostic: source must be diagnostic-only historical replay');
const result=diagnoseP25ExitV2VsFixedPairs(pairs);if(result.pairedCount!==27)throw new Error(`P25 EXIT v2 loss diagnostic: expected legacy paired n=27, got ${result.pairedCount}`);
const envelope={schemaVersion:1,phase:'57.p25.exit-v2.loss-diagnostics',status:'P25_EXIT_V2_LOSS_DIAGNOSTIC_EVIDENCE',createdAt:new Date().toISOString(),source:{runId:sourceRunId?Number(sourceRunId):null,artifact:sourceArtifact??null,digest:sourceDigest??null,lineageManifestHeadSha256:replay?.lineageManifestHeadSha256??null,policySha256:replay?.policySha256??null},result,methodology:P25_EXIT_V2_LOSS_DIAGNOSTIC_SAFETY,safety:P25_EXIT_V2_LOSS_DIAGNOSTIC_SAFETY};
fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,JSON.stringify(envelope,null,2)+'\n');
console.log(JSON.stringify({status:envelope.status,pairedCount:result.pairedCount,worseCount:result.worseCount,betterCount:result.betterCount,equalCount:result.equalCount,byCategory:result.byCategory,byState:result.byState,source:envelope.source},null,2));
