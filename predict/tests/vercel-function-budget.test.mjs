import assert from "node:assert/strict";
import { readdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import test from "node:test";

const API_DIRECTORY = fileURLToPath(new URL("../../api/", import.meta.url));
const HOBBY_FUNCTION_LIMIT = 12;

async function javascriptFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(
    entries.map(async (entry) => {
      const path = `${directory}/${entry.name}`;

      if (entry.isDirectory()) return javascriptFiles(path);
      return entry.isFile() && entry.name.endsWith(".js") ? [path] : [];
    }),
  );

  return nested.flat();
}

test("Vercel Hobby function entrypoints stay within the project budget", async () => {
  const files = await javascriptFiles(API_DIRECTORY);

  assert.ok(
    files.length <= HOBBY_FUNCTION_LIMIT,
    `Vercel function entrypoints: ${files.length}/${HOBBY_FUNCTION_LIMIT}\n${files.join("\n")}`,
  );
});
