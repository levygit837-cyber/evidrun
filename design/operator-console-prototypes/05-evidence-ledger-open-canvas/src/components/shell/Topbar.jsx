import { BookOpen, ChatCircle, SlidersHorizontal } from "@phosphor-icons/react";
import { Button, IconButton } from "../primitives/Controls.jsx";

export function Topbar({ onUtility, onOpenChat, chatOpen }) {
  return (
    <header className="topbar">
      <div className="topbar__date" aria-label="Data da demonstração">
        <time dateTime="2026-07-23">23 jul 2026</time>
        <span aria-hidden="true">/</span>
        <span>America/Asuncion</span>
      </div>
      <div className="topbar__actions">
        <Button variant="quiet" icon={BookOpen} onClick={() => onUtility("Documentação não faz parte deste stub isolado.")}>Documentação</Button>
        <Button variant="quiet" icon={SlidersHorizontal} onClick={() => onUtility("Configurações permanecem somente como superfície visual neste protótipo.")}>Configurações</Button>
        <IconButton className="topbar__chat" label={chatOpen ? "Focar Chat" : "Abrir Chat"} icon={ChatCircle} onClick={onOpenChat} />
      </div>
    </header>
  );
}
