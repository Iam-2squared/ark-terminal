'use strict';
// Test-only preload; never imported into production/provider/model modules.
if (process.env.ARK_TEST_OFFLINE !== '1') throw new Error('OFFLINE_FLAG_REQUIRED');
const fs = require('node:fs');
const path = require('node:path');
const {syncBuiltinESMExports} = require('node:module');
const audit = process.env.ARK_OFFLINE_AUDIT_DIR;
if (!audit || !fs.statSync(audit).isDirectory()) throw new Error('OFFLINE_AUDIT_DIR_REQUIRED');
const file = path.join(audit, `node-${process.pid}.jsonl`);
let blocked = 0;
const record = item => fs.appendFileSync(file, JSON.stringify({pid: process.pid, ...item})+'\n');
record({event: 'GUARD_LOADED'});
function deny(api) { return function() {
  blocked++;
  record({event: 'BLOCKED_BEFORE_NETWORK', api});
  process.exitCode = 97;
  throw new Error(`ARK_OFFLINE_NETWORK_FORBIDDEN:${api}`);
}; }
globalThis.fetch = deny('fetch');
if (globalThis.WebSocket) globalThis.WebSocket = deny('WebSocket');
for (const name of ['http','https']) for (const method of ['request','get'])
  require('node:'+name)[method] = deny(name+'.'+method);
require('node:http2').connect = deny('http2.connect');
require('node:net').Socket.prototype.connect = deny('net.Socket.connect');
require('node:tls').connect = deny('tls.connect');
require('node:dgram').createSocket = deny('dgram.createSocket');
const dns = require('node:dns');
for (const method of Object.keys(dns)) if (/^(lookup|resolve|reverse)/.test(method) && typeof dns[method]==='function')
  dns[method] = deny('dns.'+method);
for (const method of Object.keys(dns.promises)) if (/^(lookup|resolve|reverse)/.test(method) && typeof dns.promises[method]==='function')
  dns.promises[method] = deny('dns.promises.'+method);
syncBuiltinESMExports();
process.on('exit', () => {
  record({event: 'GUARD_EXIT', blockedAttempts: blocked});
  if (blocked) process.exitCode = 97; // catching the exception cannot turn it into PASS
});
