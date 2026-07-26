import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import initWasm, { generate_sign } from "./pzds_wasm_glue_03574d3f.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const wasmPath = path.join(__dirname, "ad96acb6.wasm");

globalThis.self ??= globalThis;
globalThis.window ??= globalThis;
globalThis.global ??= globalThis;
Object.defineProperty(globalThis, Symbol.toStringTag, {
  value: "Window",
  configurable: true,
});
globalThis.location ??= {
  href: "https://www.pzds.com/goodsList/7/6",
  hostname: "www.pzds.com",
};

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  return Buffer.concat(chunks).toString("utf8");
}

async function main() {
  const input = JSON.parse(await readStdin());
  const dataJson = typeof input.dataJson === "string" ? input.dataJson : JSON.stringify(input.data ?? {});
  const method = String(input.method || "post");
  const timestamp = String(input.timestamp || Date.now());
  const random = String(input.random || Math.floor(900000 * Math.random()) + 100000);
  const wasmBytes = await fs.readFile(wasmPath);
  await initWasm(wasmBytes);
  const sign = generate_sign(dataJson, method, timestamp, random);
  process.stdout.write(JSON.stringify({ sign, timestamp, random }) + "\n");
}

main().catch((error) => {
  process.stderr.write((error && error.stack) || String(error));
  process.exit(1);
});
