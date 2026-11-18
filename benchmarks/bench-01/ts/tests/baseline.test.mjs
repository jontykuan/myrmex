import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

test("baseline scaffold exists", () => {
  assert.ok(fs.existsSync(path.resolve("src/scheduler.ts")));
});
