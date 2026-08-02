import { readFileSync } from "node:fs";

const packageJson = JSON.parse(
  readFileSync(new URL("../package.json", import.meta.url), "utf8"),
);

const sections = [
  {
    title: "Ambientes de desenvolvimento",
    entries: [
      ["pnpm dev", "Abre o app web com backend, worker e Vite."],
      [
        "pnpm desktop:dev",
        "Abre o app Electron; o desktop supervisiona backend e worker.",
      ],
      ["pnpm dev:web", "Inicia somente o Vite; requer backend separado."],
      ["pnpm backend:dev", "Inicia somente a API local em 127.0.0.1:8765."],
      ["pnpm worker:dev", "Inicia somente o worker durável de Runs."],
      ["pnpm preview:web", "Serve o build web local para conferência."],
      ["pnpm desktop:start", "Abre o Electron usando os arquivos já compilados."],
    ],
  },
  {
    title: "Testes e verificações",
    entries: [
      ["pnpm test", "Executa contratos e todos os testes TypeScript."],
      ["pnpm test:web", "Executa os testes do renderer React."],
      ["pnpm test:desktop", "Executa os testes do Electron."],
      ["pnpm test:handshake", "Valida o handshake real do backend desktop."],
      ["pnpm test:supervision", "Valida a supervisão real de backend e worker."],
      ["pnpm typecheck:web", "Verifica os tipos do renderer React."],
      ["pnpm typecheck:desktop", "Verifica os tipos de Main e preload."],
      ["pnpm check:contracts", "Confere se schemas e tipos gerados estão atuais."],
      ["pnpm check:budget", "Verifica o orçamento estrutural do código."],
      ["pnpm check:imports", "Verifica as fronteiras de importação."],
    ],
  },
  {
    title: "Build, geração e distribuição",
    entries: [
      ["pnpm build", "Compila web, Electron Main e preload."],
      ["pnpm build:web", "Compila somente o renderer web."],
      ["pnpm build:desktop", "Compila somente Electron Main e preload."],
      ["pnpm build:sidecars", "Gera os binários Python do backend e worker."],
      ["pnpm generate:schemas", "Regenera os JSON Schemas dos contratos."],
      ["pnpm generate:contracts", "Regenera schemas e tipos TypeScript."],
      ["pnpm package:desktop", "Monta o diretório do aplicativo desktop."],
      ["pnpm make:desktop", "Gera os artefatos distribuíveis do desktop."],
    ],
  },
  {
    title: "Preparação e CLI Python",
    entries: [
      ["uv sync --extra dev", "Instala o ambiente Python de desenvolvimento."],
      ["pnpm install", "Instala as dependências Node.js."],
      ["uv run evidrun init", "Inicializa o diretório de dados local."],
      ["uv run evidrun doctor", "Diagnostica a instalação e o provider."],
      ["uv run evidrun demo", "Carrega e executa o demo determinístico."],
      ["uv run evidrun --help", "Lista todos os comandos da CLI Evidrun."],
      ["uv run evidrun-worker --help", "Lista as opções do worker."],
    ],
  },
];

const packageCommands = new Set([
  "commands",
  "help",
  ...sections.flatMap(({ entries }) =>
    entries
      .map(([command]) => /^pnpm ([^ ]+)$/.exec(command)?.[1])
      .filter((command) => command && command !== "install"),
  ),
]);
const undocumented = Object.keys(packageJson.scripts).filter(
  (script) => !packageCommands.has(script),
);

if (undocumented.length > 0) {
  throw new Error(`Scripts sem descrição: ${undocumented.join(", ")}`);
}

const width = Math.max(
  ...sections.flatMap(({ entries }) => entries.map(([command]) => command.length)),
);

console.log("Evidrun — comandos do projeto\n");
for (const { title, entries } of sections) {
  console.log(title);
  for (const [command, description] of entries) {
    console.log(`  ${command.padEnd(width)}  ${description}`);
  }
  console.log();
}

console.log("Use `pnpm commands` ou `pnpm run help`; `pnpm help` pertence ao próprio pnpm.");
