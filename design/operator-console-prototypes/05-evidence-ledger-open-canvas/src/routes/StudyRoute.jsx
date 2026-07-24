import { useMemo, useState } from "react";
import {
  ArrowRight,
  CheckCircle,
  ChatsCircle,
  Code,
  Cube,
  FilePlus,
  GitBranch,
  Play,
  Shield,
  WarningCircle,
} from "@phosphor-icons/react";
import { PREFLIGHTS, REVISIONS } from "../data/mockData.js";
import { Button, Notice, SegmentedControl, StatusBadge, TechnicalRef } from "../components/primitives/Controls.jsx";
import { FixtureScopeLock } from "../components/scope/FixtureScopeLock.jsx";

const VARIANTS = ["head-truncation", "tail-preservation"];

export function StudyRoute({ initialNewRevision = false, onOpenChat, navigate, project, onSelectFixture }) {
  const [revision, setRevision] = useState(initialNewRevision ? "local-005" : "rev-004");
  const [localDraft, setLocalDraft] = useState(initialNewRevision);
  const [objective, setObjective] = useState(REVISIONS[0].objective);
  const [variant, setVariant] = useState("head-truncation");
  const [showCompile, setShowCompile] = useState(true);
  const [queued, setQueued] = useState(false);

  const preflight = PREFLIGHTS[variant];
  const canEnqueue = !localDraft && preflight.decision === "admitted";
  const revisionLabel = localDraft ? "rev-local-005 · draft" : REVISIONS.find((item) => item.id === revision)?.label ?? REVISIONS[0].label;

  const compiledPreview = useMemo(() => ({
    study_revision: localDraft ? "rev-local-005" : revision,
    scenario: "root-cause-long-log",
    variant,
    repetitions: 1,
    max_turns: variant === "head-truncation" ? 3 : 1,
    stop_condition: "goal_complete",
  }), [localDraft, revision, variant]);

  const createRevision = () => {
    setRevision("local-005");
    setLocalDraft(true);
    setQueued(false);
  };

  const selectRevision = (value) => {
    setRevision(value);
    setLocalDraft(value === "local-005");
    const selected = REVISIONS.find((item) => item.id === value);
    if (selected) setObjective(selected.objective);
    setQueued(false);
  };

  if (project.id !== "crl") {
    return <FixtureScopeLock entity="Study" project={project} onBack={() => navigate("/projects")} onOpenFixture={onSelectFixture} />;
  }

  return (
    <div className="route route--study">
      <header className="route-header route-header--actions">
        <div>
          <span className="route-kicker">Study & Admission</span>
          <h1>Preservação da causa-raiz em logs longos</h1>
          <p>Edite a revisão, confira a matriz compilada e trate cada Admission como decisão para um RunSpec exato.</p>
        </div>
        <div className="route-header__actions">
          <label className="revision-select">
            <span className="sr-only">Selecionar revisão</span>
            <select value={revision} onChange={(event) => selectRevision(event.target.value)}>
              {REVISIONS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
              <option value="local-005">rev-local-005 · draft local</option>
            </select>
          </label>
          <Button icon={ChatsCircle} onClick={onOpenChat}>Abrir Chat</Button>
        </div>
      </header>

      <Notice title={localDraft ? "Nova revisão somente local" : "Fixture de interface com referência aceita"}>
        {localDraft
          ? "A alteração vive apenas em React. Ela não representa aceitação humana, compilação canônica ou persistência."
          : "A revisão aceita vem do pacote canônico CRL-CTX-002. A interface abaixo não criou esse record."}
      </Notice>

      <div className="study-layout">
        <section className="study-workbench">
          <div className="study-revision-editor">
            <header>
              <div><span>StudyRevision</span><h2>{revisionLabel}</h2></div>
              <StatusBadge tone={localDraft ? "warning" : "success"}>{localDraft ? "draft local" : "accepted fixture"}</StatusBadge>
            </header>
            <label htmlFor="study-objective">Objetivo da revisão</label>
            <textarea id="study-objective" rows={3} value={objective} onChange={(event) => { setObjective(event.target.value); setLocalDraft(true); setRevision("local-005"); }} />
            <p>Campos editáveis não concedem autoridade. A aceitação exige HumanAttestationRecord verificado.</p>
          </div>

          <section className="study-matrix" aria-labelledby="matrix-title">
            <header><div><h2 id="matrix-title">Matriz da Study</h2><p>1 scenario × 2 variants × 1 repetition</p></div><StatusBadge tone="neutral">2 RunSpecs previstos</StatusBadge></header>
            <div className="matrix-scenario">
              <Cube size={22} aria-hidden="true" />
              <div><small>scenario</small><strong>root-cause-long-log</strong></div>
            </div>
            <div className="matrix-variants">
              {VARIANTS.map((item) => (
                <button key={item} type="button" className={variant === item ? "is-selected" : ""} onClick={() => { setVariant(item); setQueued(false); }}>
                  <GitBranch size={20} aria-hidden="true" />
                  <span><small>variant</small><strong>{item}</strong><em>repetition 1</em></span>
                  <ArrowRight size={17} aria-hidden="true" />
                </button>
              ))}
            </div>
          </section>

          <section className="compile-preview">
            <button type="button" className="compile-preview__toggle" aria-expanded={showCompile} onClick={() => setShowCompile((value) => !value)}>
              <Code size={19} aria-hidden="true" />
              <span>Compile preview</span>
              <StatusBadge tone={localDraft ? "warning" : "neutral"}>{localDraft ? "não canônico" : variant}</StatusBadge>
            </button>
            {showCompile ? <pre><code>{JSON.stringify(compiledPreview, null, 2)}</code></pre> : null}
          </section>
        </section>

        <aside className="admission-panel" aria-labelledby="admission-title">
          <header>
            <div className="admission-panel__title"><Shield size={23} aria-hidden="true" /><div><span>Preflight por RunSpec</span><h2 id="admission-title">Admission</h2></div></div>
            <StatusBadge tone={localDraft ? "neutral" : preflight.decision === "admitted" ? "success" : "danger"}>{localDraft ? "indisponível" : preflight.decision}</StatusBadge>
          </header>

          <SegmentedControl
            label="RunSpec do preflight"
            value={variant}
            onChange={(value) => { setVariant(value); setQueued(false); }}
            options={VARIANTS.map((item) => ({ value: item, label: item }))}
          />

          {localDraft ? (
            <Notice title="Compile uma revisão aceita primeiro">Este draft local ainda não produz RunSpec nem AdmissionRecord.</Notice>
          ) : preflight.decision === "rejected" ? (
            <div className="admission-result admission-result--rejected">
              <div className="admission-result__issue"><WarningCircle size={22} aria-hidden="true" /><div><span>Issue</span><TechnicalRef>{preflight.issue}</TechnicalRef></div></div>
              <div className="contract-mismatch" aria-label="Comparação do contrato solicitado e suportado">
                <div><span>RunSpec solicita</span><strong>{preflight.requested}</strong></div>
                <WarningCircle size={24} aria-hidden="true" />
                <div><span>Runner suporta</span><strong>{preflight.supported}</strong></div>
              </div>
              <p>{preflight.explanation}</p>
            </div>
          ) : (
            <div className="admission-result admission-result--admitted">
              <CheckCircle size={34} aria-hidden="true" />
              <div><strong>Compatível com o runner ativo</strong><p>{preflight.explanation}</p></div>
            </div>
          )}

          {!localDraft ? (
            <dl className="admission-facts">
              <div><dt>RunSpec</dt><dd><TechnicalRef>{variant}</TechnicalRef></dd></div>
              <div><dt>AdmissionRecord</dt><dd><TechnicalRef>{preflight.admissionId}</TechnicalRef></dd></div>
              <div><dt>Authority adapter</dt><dd>não requerido para este stub</dd></div>
            </dl>
          ) : null}

          {queued ? <Notice tone="success" title="Solicitação local preparada">O stub marcou o RunSpec admitido para a próxima tela. Nenhum backend record foi gravado.</Notice> : null}

          <div className="admission-panel__actions">
            <Button icon={FilePlus} onClick={createRevision}>Criar nova revisão</Button>
            <Button variant="primary" icon={Play} disabled={!canEnqueue} onClick={() => setQueued(true)}>Enfileirar RunSpec</Button>
          </div>
          <p className="admission-panel__hint">{canEnqueue ? "Disponível porque decision=admitted para este RunSpec exato." : "Enqueue bloqueado sem revision aceita e decision=admitted."}</p>
          {queued ? <Button className="admission-panel__continue" onClick={() => navigate("/runs")}>Ir para Runs</Button> : null}
        </aside>
      </div>
    </div>
  );
}
