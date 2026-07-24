import { IdentificationBadge, UserCircle } from "@phosphor-icons/react";
import { motion, useReducedMotion } from "motion/react";
import { ObservableActivity } from "./ObservableActivity.jsx";

export function ConversationFeed({ state }) {
  const reduceMotion = useReducedMotion();
  const lastAgentIndex = state.messages.findLastIndex(
    (message) => message.author === "Lab Agent",
  );

  return (
    <section className="conversation-feed" aria-label="Conversa do Lab">
      {state.messages.map((message, index) => {
        const agent = message.author === "Lab Agent";
        const Icon = agent ? IdentificationBadge : UserCircle;
        const showActivity = agent && index === lastAgentIndex;
        return (
          <motion.article
            className={`message-row${agent ? " is-agent" : " is-user"}`}
            key={message.id}
            initial={reduceMotion ? false : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
          >
            <Icon aria-hidden="true" size={26} />
            <div className="message-body">
              <header>
                <strong>{message.author}</strong>
                {message.draft ? <span className="draft-label">Rascunho</span> : null}
                <time>{message.time}</time>
              </header>
              <p>{message.text}</p>
              {showActivity ? (
                <ObservableActivity activity={state.activity} failure={state.error} />
              ) : null}
            </div>
          </motion.article>
        );
      })}
    </section>
  );
}
