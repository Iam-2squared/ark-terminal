/** Private local source/receipt I/O; no Excel, broker, network or model calls. */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {DAILY_PLAN_SCHEMA, ORIGINAL_SYMBOLS_SHA256, parseRequestSymbols, lastCompletedSession,
  requiredDailySessions, jstNow, summarizeDailyCaptures, inspectDailyCapture} from '../runtime/no11_rss_daily_trend_census.mjs';
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const here = path.dirname(fileURLToPath(import.meta.url));
const codeFiles = ['tools/no11_rss_daily_trend_census.mjs','runtime/no11_rss_daily_trend_census.mjs',
  'runtime/no11_existing_selector_trend_prefilter.mjs','runtime/jpx_cash_calendar_2026_2027.mjs',
  'windows/Run-No11RssDailyTrendCensusReadOnly.ps1'];
export function codeIdentity() { return hash(JSON.stringify(codeFiles.map(name => [name, hash(fs.readFileSync(path.join(here, '..', name)))]))); }
function readJson(filename) {
  const st = fs.lstatSync(filename);
  if (!st.isFile() || st.isSymbolicLink() || st.size > 4000000) throw Error('NO11_DAILY_FILE_INVALID');
  return JSON.parse(fs.readFileSync(filename, 'utf8').replace(/^\uFEFF/, ''));
}
export function immutable(filename, value) {
  const data = Buffer.from(JSON.stringify(value) + '\n');
  try { fs.writeFileSync(filename, data, {flag:'wx'}); }
  catch (error) { if (error.code !== 'EEXIST' || !fs.readFileSync(filename).equals(data)) throw error; }
  return hash(data);
}
function validatePlan(plan) {
  const {planId, ...rest} = plan;
  if (hash(JSON.stringify(rest)) !== planId || plan.codeSha256 !== codeIdentity()) throw Error('NO11_DAILY_PLAN_PIN_MISMATCH');
  summarizeDailyCaptures(plan, []);
  return plan;
}
export function loadCaptures(run, plan) {
  const result = [], seen = new Set(), sourceDir = path.join(run, 'sources');
  if (fs.lstatSync(sourceDir).isSymbolicLink()) throw Error('NO11_DAILY_SYMLINK_REJECTED');
  for (const name of fs.readdirSync(sourceDir).sort()) {
    if (name.endsWith('.pending')) continue; // incomplete write is not a completed capture
    const m = /^([0-9A-Z]{4}\.T)-([a-f0-9]{64})\.json$/.exec(name);
    if (!m) throw Error('NO11_DAILY_SOURCE_NAME_INVALID');
    const filename = path.join(sourceDir, name), value = readJson(filename);
    if (hash(fs.readFileSync(filename)) !== m[2] || value.symbol !== m[1] || seen.has(value.symbol)) throw Error('NO11_DAILY_SOURCE_HASH_OR_IDENTITY_MISMATCH');
    inspectDailyCapture(value, plan); seen.add(value.symbol); result.push(value);
  }
  return result;
}
export function makePlan(symbolBytes, now, codeSha256) {
  const sourceSymbolsSha256 = hash(symbolBytes);
  if (sourceSymbolsSha256 !== ORIGINAL_SYMBOLS_SHA256) throw Error('NO11_DAILY_ORIGINAL_SYMBOL_LIST_PIN_MISMATCH');
  const {symbols, baselineAdded} = parseRequestSymbols(symbolBytes.toString('utf8'));
  const asOfSession = lastCompletedSession(now);
  const body = {schemaId: DAILY_PLAN_SCHEMA, createdAtJst: now, asOfSession,
    expectedSessions: requiredDailySessions(asOfSession), sourceSymbolsSha256, codeSha256,
    symbols, baselineAdded, priceBasisCertified: false, productionReady: false, orderTransmission: false};
  return {planId: hash(JSON.stringify(body)), ...body};
}
export function runCli(args) {
  const [action, ...rest] = args, flags = {};
  if (!['plan','report'].includes(action) || rest.length % 2) throw Error('NO11_DAILY_ARGUMENTS_INVALID');
  for (let i = 0; i < rest.length; i += 2) {
    if (!['--root','--symbols','--run'].includes(rest[i]) || flags[rest[i]]) throw Error('NO11_DAILY_ARGUMENTS_INVALID');
    flags[rest[i]] = rest[i + 1];
  }
  if (action === 'plan') {
    const root = flags['--root'];
    if (!root || !path.isAbsolute(root) || !flags['--symbols']) throw Error('NO11_DAILY_PRIVATE_ROOT_REQUIRED');
    const resolvedRoot = path.resolve(root), repoRoot = path.resolve(here, '../../..');
    if (resolvedRoot === repoRoot || resolvedRoot.startsWith(repoRoot + path.sep)) throw Error('NO11_DAILY_PRIVATE_ROOT_IN_REPO');
    fs.mkdirSync(root, {recursive: true});
    if (fs.lstatSync(root).isSymbolicLink()) throw Error('NO11_DAILY_SYMLINK_REJECTED');
    const candidate = makePlan(fs.readFileSync(flags['--symbols']), jstNow(), codeIdentity());
    const run = path.join(root, 'daily-' + candidate.asOfSession + '-' + candidate.codeSha256.slice(0,16));
    fs.mkdirSync(run, {recursive: true});
    if (fs.lstatSync(run).isSymbolicLink()) throw Error('NO11_DAILY_SYMLINK_REJECTED');
    fs.mkdirSync(path.join(run, 'sources'), {recursive: true});
    const planFile = path.join(run, 'plan.json');
    if (!fs.existsSync(planFile)) immutable(planFile, candidate);
    const plan = validatePlan(readJson(planFile));
    if (plan.sourceSymbolsSha256 !== candidate.sourceSymbolsSha256 || plan.asOfSession !== candidate.asOfSession) throw Error('NO11_DAILY_RESUME_SCOPE_MISMATCH');
    const captures = loadCaptures(run, plan), have = new Set(captures.map(x => x.symbol));
    console.log(JSON.stringify({run, plan, resumed: captures.length, remaining: plan.symbols.filter(x => !have.has(x))}));
  } else {
    const run = flags['--run'];
    if (!run || !path.isAbsolute(run) || fs.lstatSync(run).isSymbolicLink()) throw Error('NO11_DAILY_RUN_REQUIRED');
    const plan = validatePlan(readJson(path.join(run, 'plan.json'))), captures = loadCaptures(run, plan);
    const {summary, details} = summarizeDailyCaptures(plan, captures);
    const detailsSha = hash(Buffer.from(JSON.stringify(details) + '\n'));
    immutable(path.join(run, 'private-details-' + detailsSha.slice(0,16) + '.json'), details);
    summary.privateDetailsSha256 = detailsSha;
    summary.sourceManifestSha256 = hash(JSON.stringify(fs.readdirSync(path.join(run, 'sources')).filter(x => x.endsWith('.json')).sort()));
    // Public shareable summary contains aggregates and hashes, not symbols/prices or local paths.
    const reportHash = hash(Buffer.from(JSON.stringify(summary) + '\n'));
    const report = path.join(run, 'no11-daily-trend-summary-' + reportHash.slice(0,16) + '.json');
    immutable(report, summary);
    console.log('NO11_DAILY_TREND_CENSUS=' + summary.status);
    console.log('NO11_DAILY_STRUCTURE_COUNTS=' + JSON.stringify(summary.observedStructureCounts));
    console.log('NO11_DAILY_TREND_REPORT=' + report);
    console.log('NO11_PRODUCTION_READY=False\nORDER_TRANSMISSION=False');
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  try { runCli(process.argv.slice(2)); }
  catch (error) { console.error(/^NO11_|^NO12_/.test(error.message) ? error.message : 'NO11_DAILY_LOCAL_IO_FAILURE'); process.exitCode = 2; }
}
