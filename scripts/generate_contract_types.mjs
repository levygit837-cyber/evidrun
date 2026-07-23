import { readFile, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import process from "node:process";

import { compileFromFile } from "json-schema-to-typescript";

const root = resolve(import.meta.dirname, "..");
const source = resolve(root, "schemas/generated/contracts/catalog-v1.json");
const target = resolve(root, "apps/web/src/generated/contracts.ts");
const check = process.argv.includes("--check");

const generated = await compileFromFile(source, {
  bannerComment:
    "/* Generated from Pydantic JSON Schema. Do not edit by hand. */",
  style: {
    bracketSpacing: true,
    printWidth: 100,
    semi: true,
    singleQuote: false,
    tabWidth: 2,
    trailingComma: "all",
    useTabs: false,
  },
});

if (check) {
  const current = await readFile(target, "utf8").catch(() => "");
  if (current !== generated) {
    throw new Error("Generated TypeScript contract types are stale");
  }
} else {
  await mkdir(dirname(target), { recursive: true });
  await writeFile(target, generated, "utf8");
}
