import { CommandRail } from "./CommandRail.jsx";
import { AdaptiveChat } from "./AdaptiveChat.jsx";
import { useOperator } from "../context/OperatorContext.jsx";

export function OperatorShell({ children }) {
  const { state } = useOperator();
  return (
    <div className={`operator-shell operator-shell--chat-${state.chat.mode}`}>
      <a className="skip-link" href="#main-content">Pular para o conteúdo</a>
      <CommandRail />
      <div className="operator-shell__body">
        <main id="main-content" tabIndex="-1">{children}</main>
        <AdaptiveChat />
      </div>
    </div>
  );
}
