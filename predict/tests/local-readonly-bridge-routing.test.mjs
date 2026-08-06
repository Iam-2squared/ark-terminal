import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const sourcePath = path.resolve(here, "../../real-account-home.js");
const source = fs.readFileSync(sourcePath, "utf8");

test("local frontends force the localhost RSS bridge instead of relative API overrides", () => {
  assert.match(source, /LOCAL_FRONTEND_HOSTS/);
  assert.match(source, /DEFAULT_LOCAL_REAL_ACCOUNT_API_BASE/);
  assert.match(source, /if \(isLocalFrontend\(\)\)/);
  assert.match(source, /find\(isAbsoluteLocalBridgeUrl\)/);
  assert.match(source, /return explicitLocalValue \|\| DEFAULT_LOCAL_REAL_ACCOUNT_API_BASE/);
});

test("local bridge failure does not fall back to the Live Server API path", () => {
  assert.match(source, /if \(isLocalFrontend\(\)\) throw localError/);
  assert.match(source, /REMOTE_REAL_ACCOUNT_API_BASE = "\/api\/broker-readonly"/);
});

test("read-only and no-order safety remain explicit", () => {
  assert.match(source, /"X-Ark-Read-Only": "true"/);
  assert.match(source, /注文機能は引き続き無効です/);
  assert.doesNotMatch(source, /RssStockOrder/);
});
