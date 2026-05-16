/**
 * Hermes → Cursor SDK（本機 Agent）
 * stdin: JSON { system, user, cwd, model }
 * stdout: JSON { ok, status, text, error? }
 */
import { readFileSync } from "node:fs";
import { Agent } from "@cursor/sdk";

const raw = readFileSync(0, "utf8");
const input = JSON.parse(raw);
const apiKey = process.env.CURSOR_API_KEY;
if (!apiKey) {
  console.log(JSON.stringify({ ok: false, error: "CURSOR_API_KEY 未設定" }));
  process.exit(1);
}

const system = String(input.system || "");
const user = String(input.user || "");
const cwd = String(input.cwd || process.cwd());
const modelId = String(input.model || process.env.HERMES_CURSOR_MODEL || "composer-2");

const prompt = `${system}\n\n---\n\n${user}`;

try {
  const result = await Agent.prompt(prompt, {
    apiKey,
    model: { id: modelId },
    local: { cwd, settingSources: [] },
  });
  const ok = result.status === "finished";
  console.log(
    JSON.stringify({
      ok,
      status: result.status,
      text: result.result ?? "",
      error: ok ? undefined : "Cursor run 未成功完成",
    }),
  );
  process.exit(ok ? 0 : 2);
} catch (err) {
  console.log(
    JSON.stringify({
      ok: false,
      error: err instanceof Error ? err.message : String(err),
    }),
  );
  process.exit(1);
}
