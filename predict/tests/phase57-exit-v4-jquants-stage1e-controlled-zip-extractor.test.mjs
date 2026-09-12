import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import {deflateRawSync, gunzipSync, gzipSync} from 'node:zlib';
import {
  ALLOWED_SESSIONS,
  SAFETY,
  deleteTemporaryFile,
  extractAllowedSession,
  validateLineage,
} from '../../scripts/lib/phase57-stage1e-controlled-zip-extractor.mjs';

function crc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) { crc ^= byte; for (let bit = 0; bit < 8; bit += 1) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0); }
  return (crc ^ 0xffffffff) >>> 0;
}

function zip(entries) {
  const local = [];
  const central = [];
  let offset = 0;
  for (const entry of entries) {
    const name = Buffer.from(entry.name);
    const content = Buffer.isBuffer(entry.content) ? entry.content : Buffer.from(entry.content);
    const compressed = deflateRawSync(content);
    const lh = Buffer.alloc(30);
    lh.writeUInt32LE(0x04034b50, 0); lh.writeUInt16LE(20, 4); lh.writeUInt16LE(0x800, 6); lh.writeUInt16LE(8, 8);
    lh.writeUInt32LE(crc32(content), 14); lh.writeUInt32LE(compressed.length, 18); lh.writeUInt32LE(content.length, 22); lh.writeUInt16LE(name.length, 26);
    local.push(lh, name, compressed);
    const ch = Buffer.alloc(46);
    ch.writeUInt32LE(0x02014b50, 0); ch.writeUInt16LE(20, 4); ch.writeUInt16LE(20, 6); ch.writeUInt16LE(0x800, 8); ch.writeUInt16LE(8, 10);
    ch.writeUInt32LE(crc32(content), 16); ch.writeUInt32LE(compressed.length, 20); ch.writeUInt32LE(content.length, 24); ch.writeUInt16LE(name.length, 28); ch.writeUInt32LE(offset, 42);
    central.push(ch, name);
    offset += lh.length + name.length + compressed.length;
  }
  const centralBytes = Buffer.concat(central);
  const eocd = Buffer.alloc(22);
  eocd.writeUInt32LE(0x06054b50, 0); eocd.writeUInt16LE(entries.length, 8); eocd.writeUInt16LE(entries.length, 10);
  eocd.writeUInt32LE(centralBytes.length, 12); eocd.writeUInt32LE(offset, 16);
  return Buffer.concat([...local, centralBytes, eocd]);
}

function sessionMembers(date, trap = false) {
  if (trap) return [
    {name: `${date}.features.json.gz`, content: Buffer.from('TRAP_UNAPPROVED_CONTENT')},
    {name: `${date}.bars.json.gz`, content: Buffer.from('TRAP_UNAPPROVED_CONTENT')},
    {name: `${date}.manifest.json`, content: 'TRAP_UNAPPROVED_CONTENT'},
  ];
  const features = {sessionDate: date, events: [{sessionDate: date, symbol: 'TEST', futureReturn: 9, nested: {mfeBps: 2, direction: 1}}], points: []};
  const bars = [{symbol: 'TEST', bars: [{sessionDate: date, close: 100, futureVolume: 999}]}];
  const manifest = {sessionDate: date, labelsGenerated: false, featureSha256: 'a'.repeat(64), barsSha256: 'b'.repeat(64)};
  return [
    {name: `${date}.features.json.gz`, content: gzipSync(Buffer.from(JSON.stringify(features)))},
    {name: `${date}.bars.json.gz`, content: gzipSync(Buffer.from(JSON.stringify(bars)))},
    {name: `${date}.manifest.json`, content: JSON.stringify(manifest)},
  ];
}

const unapproved = ['2025-08-28','2025-08-29','2025-09-01','2025-09-02','2025-09-03','2025-09-04','2025-09-05','2025-09-08','2025-09-09'];
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage1e-'));

function runSynthetic(extra = []) {
  const zipPath = path.join(root, `fixture-${Math.random().toString(16).slice(2)}.zip`);
  const outputDir = `${zipPath}.subset`;
  const bytes = zip([...ALLOWED_SESSIONS.flatMap((date) => sessionMembers(date)), ...unapproved.flatMap((date) => sessionMembers(date, true)), ...extra]);
  fs.writeFileSync(zipPath, bytes);
  const hash = createHash('sha256').update(bytes).digest('hex');
  const lineage = {runId: 1, artifactId: 1, artifactName: 'synthetic', artifactDigest: `sha256:${hash}`, expectedContainerSha256: hash};
  return {zipPath, outputDir, lineage};
}

test('synthetic ZIP extracts one approved session and never reads nine unapproved session bodies', () => {
  const fixture = runSynthetic();
  const result = extractAllowedSession({...fixture, sessionDate: '2025-08-27'});
  assert.equal(result.approvedMembersRead, 3);
  assert.equal(result.unapprovedContentReads, 0);
  assert.equal(result.goldenRows, 1);
  assert.match(result.subsetSha256, /^[0-9a-f]{64}$/);
  const feature = JSON.parse(gunzipSync(fs.readFileSync(path.join(fixture.outputDir, '2025-08-27.features.json.gz'))));
  assert.equal(feature.events[0].futureReturn, undefined);
  assert.equal(feature.events[0].nested.mfeBps, undefined);
  assert.equal(feature.events[0].nested.direction, 1);
});

test('default deny rejects unapproved session request', () => {
  const fixture = runSynthetic();
  assert.throws(() => extractAllowedSession({...fixture, sessionDate: '2025-08-28'}), /UNAPPROVED_SESSION/);
});

test('ambiguous multisession filename blocks before member content is read', () => {
  const fixture = runSynthetic([{name: '2025-08-27_2025-10-09.features.json.gz', content: 'trap'}]);
  assert.throws(() => extractAllowedSession({...fixture, sessionDate: '2025-08-27'}), /MULTISESSION_MEMBER_BLOCKED/);
});

test('path traversal, nested archive and unexpected approved extension are denied', () => {
  for (const [name, pattern] of [['../escape.json', /PATH_TRAVERSAL/], ['payload.zip', /NESTED_ARCHIVE/], ['2025-08-27.csv', /UNEXPECTED_APPROVED_SESSION_MEMBER/]]) {
    const fixture = runSynthetic([{name, content: 'trap'}]);
    assert.throws(() => extractAllowedSession({...fixture, sessionDate: '2025-08-27'}), pattern);
  }
});

test('duplicate member is deterministically denied', () => {
  const fixture = runSynthetic([{name: '2025-08-27.manifest.json', content: '{}'}]);
  assert.throws(() => extractAllowedSession({...fixture, sessionDate: '2025-08-27'}), /DUPLICATE_MEMBER_DENIED/);
});

test('source lineage and exact container SHA are mandatory', () => {
  assert.throws(() => validateLineage({}), /RUN_ID_REQUIRED/);
  const fixture = runSynthetic();
  assert.throws(() => extractAllowedSession({...fixture, sessionDate: '2025-08-27', lineage: {...fixture.lineage, expectedContainerSha256: '0'.repeat(64)}}), /ARTIFACT_CONTAINER_DIGEST_MISMATCH/);
  assert.throws(() => extractAllowedSession({...fixture, sessionDate: '2025-08-27', lineage: {...fixture.lineage, artifactDigest: `sha256:${'0'.repeat(64)}`, expectedContainerSha256: '0'.repeat(64)}}), /CONTAINER_SHA_MISMATCH/);
});

test('temporary ZIP deletion is explicit and verified', () => {
  const fixture = runSynthetic();
  assert.deepEqual(deleteTemporaryFile(fixture.zipPath), {deleted: true, pathBasename: path.basename(fixture.zipPath)});
});

test('extractor imports no EXIT implementation and all safety flags remain false', () => {
  const source = fs.readFileSync(new URL('../../scripts/lib/phase57-stage1e-controlled-zip-extractor.mjs', import.meta.url), 'utf8');
  assert.doesNotMatch(source, /from ['"].*exit/i);
  assert.ok(Object.values(SAFETY).every((value) => value === false));
});

test.after(() => fs.rmSync(root, {recursive: true, force: true}));
