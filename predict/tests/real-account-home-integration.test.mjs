import test from "node:test";
import assert from "node:assert/strict";
import {
  readFile,
} from "node:fs/promises";

const repositoryRoot =
  new URL(
    "../../",
    import.meta.url,
  );

async function readRootFile(path) {
  return readFile(
    new URL(
      path,
      repositoryRoot,
    ),
    "utf8",
  );
}

test(
  "Home scriptが実口座READ ONLYモジュールを読み込む",
  async () => {
    const script =
      await readRootFile(
        "script.js",
      );

    assert.equal(
      script.includes(
        'import("./real-account-home.js")',
      ),
      true,
    );
  },
);

test(
  "実口座HomeモジュールはGET読み取りだけを使用する",
  async () => {
    const source =
      await readRootFile(
        "real-account-home.js",
      );

    assert.equal(
      source.includes(
        'method: "GET"',
      ),
      true,
    );

    assert.equal(
      source.includes(
        "submitOrder",
      ),
      false,
    );

    assert.equal(
      source.includes(
        "cancelOrder",
      ),
      false,
    );

    assert.equal(
      source.includes(
        "approvalToken",
      ),
      false,
    );
  },
);

test(
  "実口座カードには注文操作を置かない",
  async () => {
    const source =
      await readRootFile(
        "real-account-home.js",
      );

    assert.equal(
      source.includes(
        "実口座",
      ),
      true,
    );

    assert.equal(
      source.includes(
        "読み取り専用",
      ),
      true,
    );

    assert.equal(
      source.includes(
        "注文する",
      ),
      false,
    );

    assert.equal(
      source.includes(
        "売買する",
      ),
      false,
    );
  },
);

test(
  "PWAキャッシュに実口座Home資産を含める",
  async () => {
    const serviceWorker =
      await readRootFile(
        "service-worker.js",
      );

    assert.equal(
      serviceWorker.includes(
        '"./real-account-home.js"',
      ),
      true,
    );

    assert.equal(
      serviceWorker.includes(
        '"./real-account-home.css"',
      ),
      true,
    );
  },
);
