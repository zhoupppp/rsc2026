import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test("TalentDetailView overlay header uses close icon and supports overlay mode", () => {
  const filePath = path.resolve(__dirname, "../src/components/TalentDetailView.tsx");
  const text = fs.readFileSync(filePath, "utf8");

  assert.match(text, /mode\?:\s*"overlay"\s*\|\s*"page"/);
  assert.match(text, /aria-label="关闭弹窗"/);
  assert.match(text, /mode\s*===\s*"overlay"/);
});

