import {
  Check,
  CircleNotch,
  Code,
  FileText,
  Lightning,
  Warning,
} from "@phosphor-icons/react";
import { motion, useReducedMotion } from "motion/react";
import { StatusBadge, TechnicalRef } from "../primitives/Controls.jsx";

const STEPS = [
  "Preparando contexto autorizado",
  "Lendo referências autorizadas",
  "Preparando draft para revisão",
];

export function LedgerCursor() {
  const reduceMotion = useReducedMotion();
  return (
    <div className="ledger-cursor" role="status" aria-label="Lab Agent processando">
      <div className="ledger-cursor__track" aria-hidden="true">
        <motion.span
          animate={reduceMotion ? { x: 32 } : { x: [0, 54, 18, 68] }}
          transition={reduceMotion ? { duration: 0 } : { duration: 1.2, repeat: Infinity, ease: [0.16, 1, 0.3, 1] }}
        />
      </div>
      <span>Resolvendo referências do stub</span>
    </div>
  );
}

export function ObservableActivity({ phase, step }) {
  return (
    <section className="observable-activity" aria-labelledby="observable-title">
      <header>
        <div>
          <Lightning size={18} aria-hidden="true" />
          <h3 id="observable-title">Atividade observável</h3>
        </div>
        <StatusBadge tone={phase === "failure" ? "danger" : phase === "success" ? "success" : phase === "running" ? "info" : "neutral"}>
          {phase === "failure" ? "falha" : phase === "success" ? "concluída" : phase === "running" ? "em execução" : "ociosa"}
        </StatusBadge>
      </header>
      <p>Progresso operacional exposto pelo stub. Nenhum raciocínio privado é exibido.</p>
      <ol>
        {STEPS.map((label, index) => {
          const complete = phase === "success" || index < step;
          const active = phase === "running" && index === step;
          return (
            <li key={label} className={complete ? "is-complete" : active ? "is-active" : ""}>
              <span>{complete ? <Check size={13} weight="bold" /> : active ? <CircleNotch size={14} /> : index + 1}</span>
              {label}
            </li>
          );
        })}
      </ol>
    </section>
  );
}

export function ToolCallBlock() {
  return (
    <section className="agent-block agent-block--tool" aria-label="Tool Call ilustrativa">
      <header>
        <Code size={18} aria-hidden="true" />
        <strong>Tool Call</strong>
        <StatusBadge tone="info">contexto ilustrativo autorizado</StatusBadge>
      </header>
      <dl>
        <div><dt>tool</dt><dd><TechnicalRef>read_text</TechnicalRef></dd></div>
        <div><dt>target</dt><dd><TechnicalRef>artifact:demo-authorized-log</TechnicalRef></dd></div>
      </dl>
    </section>
  );
}

export function ToolResultBlock() {
  return (
    <section className="agent-block agent-block--result" aria-label="Tool Result ilustrativo">
      <header>
        <FileText size={18} aria-hidden="true" />
        <strong>Tool Result</strong>
        <StatusBadge tone="neutral">stub</StatusBadge>
      </header>
      <blockquote>“...timeout ocorreu após a rotação do buffer; a causa-raiz permanece no trecho final...”</blockquote>
      <p>Excerto curto e determinístico. Não foi lido do repositório nem enviado a provider.</p>
    </section>
  );
}

export function AgentExchange({ prompt, phase, step }) {
  if (phase === "idle" && !prompt) return null;
  return (
    <div className="agent-exchange">
      {prompt ? (
        <article className="message-bubble message-bubble--user">
          <strong>Você</strong>
          <p>{prompt}</p>
        </article>
      ) : null}

      <ObservableActivity phase={phase} step={step} />

      {phase === "failure" ? (
        <div className="agent-failure" role="alert">
          <Warning size={20} aria-hidden="true" />
          <div><strong>Sequência interrompida</strong><p>Falha determinística do stub. Nenhum draft ou record foi criado.</p></div>
        </div>
      ) : null}

      {phase === "success" ? (
        <>
          <ToolCallBlock />
          <ToolResultBlock />
          <article className="message-bubble message-bubble--agent">
            <strong>Lab Agent · Draft only</strong>
            <p>Os registros ilustrativos favorecem tail-preservation. Posso preparar um draft de StudyRevision para revisão humana, sem aceitar ou executar nada em seu nome.</p>
            <div className="evidence-links">
              <TechnicalRef>run:demo-run-tail</TechnicalRef>
              <TechnicalRef>event:demo-evaluation</TechnicalRef>
              <TechnicalRef>artifact:demo-comparison</TechnicalRef>
            </div>
          </article>
        </>
      ) : null}
    </div>
  );
}
