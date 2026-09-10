import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {gunzipSync, gzipSync, inflateRawSync} from 'node:zlib';

export const ALLOWED_SESSIONS = Object.freeze(['2025-08-27', '2025-10-09', '2025-11-25']);
export const REQUIRED_SUFFIXES = Object.freeze(['features.json.gz', 'bars.json.gz', 'manifest.json']);
export const SAFETY = Object.freeze({
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  transmitted: false,
});

const EOCD = 0x06054b50;
const CENTRAL = 0x02014b50;
const LOCAL = 0x04034b50;
const DATE = /\d{4}-\d{2}-\d{2}/g;
const SHA256 = /^[0-9a-f]{64}$/;
const NESTED = /\.(?:zip|tar|tgz|tbz2?|7z|rar)$/i;
const DENIED_KEY = /^(?:labels?|targets?|outcomes?|outcomeAt|future.*|actualReturn.*|netReturn.*|mfe.*|mae.*|exit.*|profit.*|winner.*|winRate|returnAfter.*|postExit.*)$/i;

const sha256 = (bytes) => createHash('sha256').update(bytes).digest('hex');

function hashFile(filePath) {
  const hash = createHash('sha256');
  const fd = fs.openSync(filePath, 'r');
  const buffer = Buffer.alloc(64 * 1024);
  let bytes = 0;
  try {
    for (let position = 0;;) {
      const read = fs.readSync(fd, buffer, 0, buffer.length, position);
      if (read === 0) break;
      hash.update(buffer.subarray(0, read));
      position += read;
      bytes += read;
    }
  } finally {
    fs.closeSync(fd);
  }
  return {sha256: hash.digest('hex'), bytes};
}

function crc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function readRange(fd, offset, length, meter, kind, memberName = null) {
  assert(Number.isSafeInteger(offset) && offset >= 0 && Number.isSafeInteger(length) && length >= 0, 'INVALID_RANGE');
  const buffer = Buffer.alloc(length);
  const read = fs.readSync(fd, buffer, 0, length, offset);
  assert.equal(read, length, 'TRUNCATED_ZIP');
  meter.bytes[kind] += length;
  if (memberName) meter.contentReads.set(memberName, (meter.contentReads.get(memberName) ?? 0) + length);
  return buffer;
}

function validateMemberName(name) {
  assert(name.length > 0 && !name.includes('\0'), 'INVALID_MEMBER_NAME');
  assert(!name.includes('\\') && !name.startsWith('/') && !/^[A-Za-z]:/.test(name), 'PATH_TRAVERSAL_DENIED');
  const pieces = name.split('/');
  assert(!pieces.some((part) => part === '' || part === '.' || part === '..'), 'PATH_TRAVERSAL_DENIED');
  assert(!NESTED.test(name), 'NESTED_ARCHIVE_DENIED');
  const dates = name.match(DATE) ?? [];
  assert(dates.length <= 1, 'MULTISESSION_MEMBER_BLOCKED');
}

export function inspectCentralDirectory(zipPath) {
  const fd = fs.openSync(zipPath, 'r');
  const meter = {bytes: {metadata: 0, approvedContent: 0}, contentReads: new Map()};
  try {
    const size = fs.fstatSync(fd).size;
    assert(size >= 22, 'INVALID_ZIP');
    const tailLength = Math.min(size, 65557);
    const tail = readRange(fd, size - tailLength, tailLength, meter, 'metadata');
    let eocd = -1;
    for (let i = tail.length - 22; i >= 0; i -= 1) if (tail.readUInt32LE(i) === EOCD) { eocd = i; break; }
    assert(eocd >= 0, 'EOCD_NOT_FOUND');
    assert.equal(tail.readUInt16LE(eocd + 4), 0, 'MULTIDISK_ZIP_DENIED');
    assert.equal(tail.readUInt16LE(eocd + 6), 0, 'MULTIDISK_ZIP_DENIED');
    const count = tail.readUInt16LE(eocd + 10);
    const centralSize = tail.readUInt32LE(eocd + 12);
    const centralOffset = tail.readUInt32LE(eocd + 16);
    assert(count !== 0xffff && centralSize !== 0xffffffff && centralOffset !== 0xffffffff, 'ZIP64_NOT_SUPPORTED');
    assert(centralOffset + centralSize <= size, 'INVALID_CENTRAL_DIRECTORY_RANGE');
    const central = readRange(fd, centralOffset, centralSize, meter, 'metadata');
    const entries = [];
    const names = new Set();
    let cursor = 0;
    for (let index = 0; index < count; index += 1) {
      assert(cursor + 46 <= central.length && central.readUInt32LE(cursor) === CENTRAL, 'INVALID_CENTRAL_DIRECTORY');
      const flags = central.readUInt16LE(cursor + 8);
      const method = central.readUInt16LE(cursor + 10);
      const crc = central.readUInt32LE(cursor + 16);
      const compressedSize = central.readUInt32LE(cursor + 20);
      const uncompressedSize = central.readUInt32LE(cursor + 24);
      const nameLength = central.readUInt16LE(cursor + 28);
      const extraLength = central.readUInt16LE(cursor + 30);
      const commentLength = central.readUInt16LE(cursor + 32);
      const diskStart = central.readUInt16LE(cursor + 34);
      const localOffset = central.readUInt32LE(cursor + 42);
      const end = cursor + 46 + nameLength + extraLength + commentLength;
      assert(end <= central.length, 'TRUNCATED_CENTRAL_DIRECTORY');
      assert.equal(flags & 1, 0, 'ENCRYPTED_MEMBER_DENIED');
      assert.equal(diskStart, 0, 'MULTIDISK_ZIP_DENIED');
      assert([0, 8].includes(method), 'UNSUPPORTED_COMPRESSION_METHOD');
      const name = central.subarray(cursor + 46, cursor + 46 + nameLength).toString('utf8');
      validateMemberName(name);
      assert(!names.has(name), 'DUPLICATE_MEMBER_DENIED');
      names.add(name);
      entries.push({name, flags, method, crc, compressedSize, uncompressedSize, localOffset});
      cursor = end;
    }
    assert.equal(cursor, central.length, 'CENTRAL_DIRECTORY_TRAILING_BYTES');
    return {fd, size, entries, meter, close: () => fs.closeSync(fd)};
  } catch (error) {
    fs.closeSync(fd);
    throw error;
  }
}

function readApprovedMember(archive, entry) {
  const header = readRange(archive.fd, entry.localOffset, 30, archive.meter, 'approvedContent', entry.name);
  assert.equal(header.readUInt32LE(0), LOCAL, 'INVALID_LOCAL_HEADER');
  const nameLength = header.readUInt16LE(26);
  const extraLength = header.readUInt16LE(28);
  const dataOffset = entry.localOffset + 30 + nameLength + extraLength;
  const compressed = readRange(archive.fd, dataOffset, entry.compressedSize, archive.meter, 'approvedContent', entry.name);
  const content = entry.method === 0 ? compressed : inflateRawSync(compressed);
  assert.equal(content.length, entry.uncompressedSize, 'UNCOMPRESSED_SIZE_MISMATCH');
  assert.equal(crc32(content), entry.crc, 'CRC32_MISMATCH');
  return content;
}

function clean(value, counter) {
  if (Array.isArray(value)) return value.map((item) => clean(item, counter));
  if (!value || typeof value !== 'object') return value;
  const result = {};
  for (const key of Object.keys(value).sort()) {
    if (DENIED_KEY.test(key)) { counter.stripped += 1; continue; }
    result[key] = clean(value[key], counter);
  }
  return result;
}

function deterministicJsonBytes(value) {
  return Buffer.from(`${JSON.stringify(value)}\n`);
}

export function validateLineage(lineage) {
  assert(lineage && Number.isInteger(lineage.runId) && lineage.runId > 0, 'RUN_ID_REQUIRED');
  assert(Number.isInteger(lineage.artifactId) && lineage.artifactId > 0, 'ARTIFACT_ID_REQUIRED');
  assert.equal(typeof lineage.artifactName, 'string', 'ARTIFACT_NAME_REQUIRED');
  assert.match(lineage.artifactDigest ?? '', /^sha256:[0-9a-f]{64}$/, 'ARTIFACT_DIGEST_REQUIRED');
  assert.match(lineage.expectedContainerSha256 ?? '', SHA256, 'CONTAINER_SHA_REQUIRED');
  assert.equal(lineage.artifactDigest, `sha256:${lineage.expectedContainerSha256}`, 'ARTIFACT_CONTAINER_DIGEST_MISMATCH');
  return true;
}

function assertSessionPayload(name, parsed, sessionDate) {
  if (name.endsWith('.bars.json.gz')) {
    assert(Array.isArray(parsed), 'BARS_ARRAY_REQUIRED');
    for (const entry of parsed) for (const bar of entry.bars ?? []) assert.equal(bar.sessionDate, sessionDate, 'MEMBER_SESSION_MISMATCH');
    return;
  }
  assert.equal(parsed.sessionDate, sessionDate, 'MEMBER_SESSION_MISMATCH');
}

export function extractAllowedSession({zipPath, outputDir, sessionDate, lineage}) {
  assert(ALLOWED_SESSIONS.includes(sessionDate), `UNAPPROVED_SESSION:${sessionDate}`);
  validateLineage(lineage);
  const container = hashFile(zipPath);
  const containerSha256 = container.sha256;
  assert.equal(containerSha256, lineage.expectedContainerSha256, 'CONTAINER_SHA_MISMATCH');
  const archive = inspectCentralDirectory(zipPath);
  try {
    const required = new Map(REQUIRED_SUFFIXES.map((suffix) => [`${sessionDate}.${suffix}`, suffix]));
    for (const entry of archive.entries) {
      const dateTokens = entry.name.match(DATE) ?? [];
      if (dateTokens[0] === sessionDate && !required.has(entry.name)) throw Error('UNEXPECTED_APPROVED_SESSION_MEMBER');
    }
    const selected = archive.entries.filter((entry) => required.has(entry.name));
    assert.equal(selected.length, required.size, 'REQUIRED_APPROVED_MEMBER_MISSING');
    fs.mkdirSync(outputDir, {recursive: false});
    const outputs = [];
    let goldenRows = 0;
    let sourceLabelsGenerated = null;
    for (const entry of selected.sort((a, b) => a.name.localeCompare(b.name))) {
      const original = readApprovedMember(archive, entry);
      const originalSha256 = sha256(original);
      const isGzip = entry.name.endsWith('.gz');
      const jsonBytes = isGzip ? gunzipSync(original) : original;
      const parsed = JSON.parse(jsonBytes);
      assertSessionPayload(entry.name, parsed, sessionDate);
      if (entry.name.endsWith('.manifest.json')) sourceLabelsGenerated = parsed.labelsGenerated;
      const counter = {stripped: 0};
      const cleaned = clean(parsed, counter);
      const cleanJson = deterministicJsonBytes(cleaned);
      const output = isGzip ? gzipSync(cleanJson, {mtime: 0}) : cleanJson;
      const target = path.join(outputDir, entry.name);
      fs.writeFileSync(target, output, {flag: 'wx', mode: 0o600});
      if (entry.name.endsWith('.features.json.gz')) goldenRows = Array.isArray(cleaned.events) ? cleaned.events.length : 0;
      outputs.push({name: entry.name, sourceMemberSha256: originalSha256, outputSha256: sha256(output), strippedFieldCount: counter.stripped, bytes: output.length});
    }
    assert.equal(sourceLabelsGenerated, false, 'SOURCE_NOT_CONFIRMED_PRE_OUTCOME');
    const unapprovedContentReads = [...archive.meter.contentReads.entries()].filter(([name]) => !required.has(name)).reduce((sum, [, bytes]) => sum + bytes, 0);
    assert.equal(unapprovedContentReads, 0, 'UNAPPROVED_CONTENT_READ');
    const subsetCore = {sessionDate, source: lineage, containerSha256, outputs};
    return {
      ...subsetCore,
      subsetSha256: sha256(deterministicJsonBytes(subsetCore)),
      goldenRows,
      approvedMembersRead: selected.length,
      unapprovedMembers: archive.entries.length - selected.length,
      unapprovedContentReads,
      metadataBytesRead: archive.meter.bytes.metadata,
      approvedContentBytesRead: archive.meter.bytes.approvedContent,
      containerHashBytesRead: container.bytes,
      safety: SAFETY,
    };
  } finally {
    archive.close();
  }
}

export function deleteTemporaryFile(filePath) {
  fs.unlinkSync(filePath);
  assert.equal(fs.existsSync(filePath), false, 'TEMPORARY_ZIP_DELETE_FAILED');
  return {deleted: true, pathBasename: path.basename(filePath)};
}
