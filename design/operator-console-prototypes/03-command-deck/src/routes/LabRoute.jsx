import {
  ChatCenteredDots,
  FileLock,
  Fingerprint,
  ShieldCheck,
} from "@phosphor-icons/react";
import { motion } from "motion/react";
import { LocalDataFlag, PageIntro, SectionHeader } from "../components/ui.jsx";

export function LabRoute() {
  const openChat = () => window.dispatchEvent(new Event("commanddeck:open-chat"));

  return (
    <div className="route-page route-page--lab">
      <PageIntro
        action={<LocalDataFlag />}
        description="Prepare um diagnóstico com somente o objetivo e o contexto que o Subject Agent pode receber."
        icon={ChatCenteredDots}
        kicker="Home"
        title="Investigue um input autorizado"
      />

      <div className="lab-workspace">
        <motion.section
          className="lab-task"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          <SectionHeader
            description="O composer executa uma sequência determinística e nunca chama um provider real."
            title="Diagnóstico de regressão após deploy"
          />
          <div className="lab-task__prompt">
            <span className="lab-task__prompt-icon" aria-hidden="true">
              <Fingerprint size={22} weight="duotone" />
            </span>
            <div>
              <strong>Objetivo do operador</strong>
              <p>Identificar sinais observáveis de regressão no trecho de deployment log autorizado.</p>
            </div>
          </div>
          <button className="primary-button" onClick={openChat} type="button">
            <ChatCenteredDots aria-hidden="true" size={18} weight="fill" />
            Abrir composer
          </button>
        </motion.section>

        <aside className="envelope-summary" aria-label="Limites do SubjectEnvelope">
          <header>
            <FileLock aria-hidden="true" size={19} weight="duotone" />
            <div>
              <strong>SubjectEnvelope</strong>
              <span className="mono">subject-envelope-stub-003</span>
            </div>
          </header>
          <ul>
            <li><ShieldCheck aria-hidden="true" size={16} /> Objective explícito</li>
            <li><ShieldCheck aria-hidden="true" size={16} /> Contexto allowlisted</li>
            <li><ShieldCheck aria-hidden="true" size={16} /> Tool read_text local</li>
          </ul>
          <p>Chat, hidden grader e conteúdo fora do envelope não são expostos ao Subject Agent.</p>
        </aside>
      </div>
    </div>
  );
}
