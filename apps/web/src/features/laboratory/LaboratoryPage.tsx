import {
  ChevronRight,
  CircleStop,
  LoaderCircle,
  Plus,
  RefreshCw,
  RotateCcw,
  Send,
  ShieldCheck,
  Trash2,
  TriangleAlert,
  X,
} from "lucide-react";
import { useMemo } from "react";
import type { LaboratoryAdapter } from "../../data/contracts";
import {
  Button,
  IconButton,
  InlineNotice,
  Textarea,
  Tooltip,
} from "../../ui/primitives";
import { AuditActivity } from "./AuditActivity";
import { ComposerMenu } from "./ComposerMenu";
import { DemoLaboratoryAdapter } from "./DemoLaboratoryAdapter";
import {
  APPROVAL_OPTIONS,
  CONTEXT_OPTIONS,
  MODEL_OPTIONS,
  REASONING_OPTIONS,
  phaseLabels,
  samplePrompts,
} from "./laboratoryModel";
import { useLaboratoryDemo } from "./useLaboratoryDemo";
import "./laboratory.css";

export type { LaboratoryPhase } from "./laboratoryModel";

export function LaboratoryPage({ adapter }: { adapter?: LaboratoryAdapter }) {
  const laboratoryAdapter = useMemo(
    () => adapter ?? new DemoLaboratoryAdapter(),
    [adapter],
  );
  const {
    phase,
    input,
    userMessage,
    agentMessage,
    statusLog,
    tools,
    error,
    approval,
    setApproval,
    model,
    setModel,
    reasoning,
    setReasoning,
    contextItems,
    textareaRef,
    isRunning,
    conversationStarted,
    resizeTextarea,
    submit,
    cancel,
    reset,
    retry,
    handleInput,
    handleKeyDown,
    addContext,
    removeContext,
  } = useLaboratoryDemo(laboratoryAdapter);

  return (
    <section
      className="laboratory"
      data-state={phase}
      data-conversation={conversationStarted ? "started" : "fresh"}
      aria-label="Laboratory Demo"
    >
      <div
        className="laboratory-state-announcer"
        role="status"
        aria-live="polite"
      >
        {phaseLabels[phase]}
      </div>

      {conversationStarted ? (
        <div className="laboratory-conversation-scroll">
          <div className="laboratory-conversation">
            <div className="laboratory-conversation-toolbar">
              <span className="laboratory-demo-label">Demo</span>
              <Button variant="quiet" size="small" onClick={reset}>
                <RotateCcw aria-hidden="true" size={14} /> Nova demonstração
              </Button>
            </div>

            <article className="laboratory-message laboratory-user-message">
              <header>Você</header>
              <p>{userMessage}</p>
            </article>

            <article className="laboratory-message laboratory-agent-message">
              <header>
                <span>Lab Agent</span>
                <span className="laboratory-demo-label">Demo</span>
              </header>
              <AuditActivity
                statusLog={statusLog}
                tools={tools}
                phase={phase}
              />

              {isRunning ? (
                <div className="laboratory-live-activity">
                  <LoaderCircle aria-hidden="true" size={15} />
                  <span>{statusLog.at(-1) ?? "Preparando sequência Demo"}</span>
                </div>
              ) : null}

              {agentMessage ? (
                <p className="laboratory-agent-draft">{agentMessage}</p>
              ) : null}

              {phase === "cancelled" ? (
                <InlineNotice tone="warning" title="Demonstração cancelada">
                  A sequência local foi interrompida. Nenhuma ação externa foi
                  executada.
                </InlineNotice>
              ) : null}

              {phase === "failed" ? (
                <InlineNotice tone="danger" title="Falha Demo">
                  <span>{error}</span>
                  <Button variant="secondary" size="small" onClick={retry}>
                    <RefreshCw aria-hidden="true" size={13} /> Tentar novamente
                  </Button>
                </InlineNotice>
              ) : null}
            </article>
          </div>
        </div>
      ) : null}

      <div
        className="laboratory-fresh-state"
        aria-hidden={conversationStarted || phase === "unavailable"}
      >
        <span className="laboratory-demo-label">Laboratory Demo</span>
        <h1>O que você quer investigar?</h1>
        <p>
          Sequência local determinística. Nenhuma Run real ou backend é
          consultado.
        </p>
        <div
          className="laboratory-samples"
          aria-label="Perguntas de demonstração"
        >
          {samplePrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              tabIndex={conversationStarted || phase === "unavailable" ? -1 : 0}
              onClick={() => handleInput(prompt)}
            >
              <span>{prompt}</span>
              <ChevronRight aria-hidden="true" size={14} />
            </button>
          ))}
        </div>
      </div>

      {phase === "unavailable" ? (
        <div className="laboratory-unavailable">
          <TriangleAlert aria-hidden="true" size={24} />
          <h1>Laboratory indisponível</h1>
          <p>
            O adapter informado não oferece uma integração executável para esta
            tela.
          </p>
          <span>Nenhuma mensagem foi enviada.</span>
        </div>
      ) : null}

      {phase !== "unavailable" ? (
        <div className="laboratory-composer-position">
          {contextItems.length > 0 ? (
            <div
              className="laboratory-context"
              aria-label="Contexto Demo selecionado"
            >
              <span>Contexto Demo</span>
              <div>
                {contextItems.map((item) => (
                  <span className="laboratory-context-item" key={item.id}>
                    {item.label}
                    <button
                      type="button"
                      onClick={() => removeContext(item.id)}
                      aria-label={`Remover ${item.label}`}
                    >
                      <X aria-hidden="true" size={12} />
                    </button>
                  </span>
                ))}
              </div>
            </div>
          ) : null}

          <div className="laboratory-composer">
            <div className="laboratory-composer-main">
              <ComposerMenu
                compact
                label="Adicionar contexto visual Demo, não aplicado"
                value="add"
                icon={<Plus aria-hidden="true" size={17} />}
                options={CONTEXT_OPTIONS}
                onChange={addContext}
              />
              <Textarea
                ref={textareaRef}
                className="laboratory-composer-input"
                rows={1}
                value={input}
                disabled={phase === "stopping"}
                aria-label="Mensagem para a demonstração do Laboratory"
                placeholder="Pergunte sobre o contexto desta demonstração..."
                onChange={(event) => handleInput(event.target.value)}
                onInput={resizeTextarea}
                onKeyDown={handleKeyDown}
              />
              <Tooltip
                content={
                  isRunning ? "Cancelar demonstração" : "Enviar mensagem"
                }
              >
                <IconButton
                  variant={isRunning ? "danger" : "primary"}
                  className="laboratory-send-button"
                  aria-label={
                    isRunning ? "Cancelar demonstração" : "Enviar mensagem"
                  }
                  disabled={
                    phase === "stopping" ||
                    (!isRunning && input.trim().length === 0)
                  }
                  onClick={isRunning ? cancel : submit}
                >
                  {phase === "stopping" ? (
                    <LoaderCircle
                      className="laboratory-spin"
                      aria-hidden="true"
                      size={15}
                    />
                  ) : isRunning ? (
                    <CircleStop aria-hidden="true" size={16} />
                  ) : (
                    <Send aria-hidden="true" size={16} />
                  )}
                </IconButton>
              </Tooltip>
            </div>

            <div
              className="laboratory-composer-toolbar"
              aria-label="Configurações visuais da demonstração"
            >
              <span className="laboratory-config-disclaimer">
                Configuração visual Demo · não aplicada
              </span>
              <div className="laboratory-config-controls">
                <ComposerMenu
                  label="Selecionar modo de aprovação visual Demo, não aplicado"
                  value={approval}
                  icon={<ShieldCheck aria-hidden="true" size={13} />}
                  options={APPROVAL_OPTIONS}
                  onChange={setApproval}
                />
                <div className="laboratory-composer-settings">
                  <ComposerMenu
                    compact
                    label="Selecionar modelo visual Demo, não aplicado"
                    value={model}
                    options={MODEL_OPTIONS}
                    onChange={setModel}
                  />
                  <ComposerMenu
                    compact
                    label="Selecionar reasoning visual Demo, não aplicado"
                    value={reasoning}
                    options={REASONING_OPTIONS}
                    onChange={setReasoning}
                  />
                </div>
              </div>
            </div>
          </div>
          <div className="laboratory-provider-note">
            <span>Demo local determinística · nenhum provider consultado</span>
            {conversationStarted ? (
              <Tooltip content="Descartar a conversa Demo atual">
                <button
                  type="button"
                  onClick={reset}
                  aria-label="Descartar demonstração atual"
                >
                  <Trash2 aria-hidden="true" size={12} />
                </button>
              </Tooltip>
            ) : null}
          </div>
        </div>
      ) : null}
    </section>
  );
}
