import assert from "node:assert/strict";
import test from "node:test";

import {
  CLOUD_SESSION_COOKIE,
  buildCloudSessionCookie,
  constantTimeEqual,
  createCloudSessionToken,
  parseCookies,
  requestHasCloudSession,
  requestIsSameOrigin,
  resolveCloudSyncSecret,
  verifyCloudSessionToken,
} from "../../api/_cloud-auth.js";

const SECRET =
  "phase21-test-secret-at-least-sixteen-characters";

test(
  "Cloud session token is signed and expires",
  () => {
    const now = 1_800_000_000_000;
    const token = createCloudSessionToken(
      SECRET,
      {
        now,
        maxAgeSeconds: 120,
      },
    );

    assert.equal(
      verifyCloudSessionToken(
        token,
        SECRET,
        { now: now + 60_000 },
      ),
      true,
    );

    assert.equal(
      verifyCloudSessionToken(
        token,
        SECRET,
        { now: now + 121_000 },
      ),
      false,
    );

    const tampered =
      `${token.slice(0, -1)}${token.endsWith("a") ? "b" : "a"}`;

    assert.equal(
      verifyCloudSessionToken(
        tampered,
        SECRET,
        { now },
      ),
      false,
    );
  },
);

test(
  "Cloud session cookie is HttpOnly and SameSite strict",
  () => {
    const cookie = buildCloudSessionCookie(
      "signed-token",
      {
        secure: true,
        maxAgeSeconds: 120,
      },
    );

    assert.match(cookie, /HttpOnly/);
    assert.match(cookie, /SameSite=Strict/);
    assert.match(cookie, /Secure/);
    assert.match(cookie, /Path=\/api/);
    assert.match(cookie, /Max-Age=120/);
  },
);

test(
  "Request authentication reads only the signed cookie",
  () => {
    const now = 1_800_000_000_000;
    const token = createCloudSessionToken(
      SECRET,
      { now },
    );

    const request = {
      headers: {
        cookie:
          `other=value; ${CLOUD_SESSION_COOKIE}=${encodeURIComponent(token)}`,
      },
    };

    assert.equal(
      requestHasCloudSession(
        request,
        {
          environment: {
            ARK_CLOUD_SYNC_SECRET:
              SECRET,
          },
          now: now + 1_000,
        },
      ),
      true,
    );
  },
);

test(
  "Cloud sync secret requires a minimum length",
  () => {
    assert.equal(
      resolveCloudSyncSecret({
        ARK_CLOUD_SYNC_SECRET:
          "too-short",
      }),
      null,
    );

    assert.equal(
      resolveCloudSyncSecret({
        ARK_CLOUD_SYNC_SECRET:
          SECRET,
      }),
      SECRET,
    );
  },
);

test(
  "Same-origin guard rejects foreign browser origins",
  () => {
    assert.equal(
      requestIsSameOrigin({
        headers: {
          origin:
            "https://ark-terminal.vercel.app",
          host:
            "ark-terminal.vercel.app",
        },
      }),
      true,
    );

    assert.equal(
      requestIsSameOrigin({
        headers: {
          origin:
            "https://example.invalid",
          host:
            "ark-terminal.vercel.app",
        },
      }),
      false,
    );
  },
);

test(
  "Cookie parser and secret comparison are deterministic",
  () => {
    assert.deepEqual(
      parseCookies("a=1; b=two%20words"),
      {
        a: "1",
        b: "two words",
      },
    );

    assert.equal(
      constantTimeEqual("same", "same"),
      true,
    );

    assert.equal(
      constantTimeEqual("same", "different"),
      false,
    );
  },
);
