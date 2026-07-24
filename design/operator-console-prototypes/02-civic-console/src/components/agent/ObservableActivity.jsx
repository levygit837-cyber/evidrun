import {
  CaretDown,
  Check,
  FileMagnifyingGlass,
  FileText,
  WarningCircle,
} from "@phosphor-icons/react";

const icons = {
  progress: Check,
  "tool-call": FileMagnifyingGlass,
  "tool-result": FileText,
  response: Check,
};

export function ObservableActivity({ activity, failure }) {
  return (
    <details className="observable-activity" open>
      <summary>
        <span>Atividade observável</span>
        <span className="activity-count">{activity.length} eventos públicos</span>
        <CaretDown aria-hidden="true" size={16} className="summary-caret" />
      </summary>
      <div className="observable-list">
        {activity.map((event) => {
          const Icon = icons[event.kind] ?? Check;
          return (
            <div className="observable-event" key={`${event.id}-${event.time}`}>
              <Icon aria-hidden="true" size={18} />
              <div>
                <strong>{event.label}</strong>
                <span className={event.kind === "tool-call" ? "mono" : undefined}>
                  {event.detail}
                </span>
              </div>
              <time>{event.time}</time>
            </div>
          );
        })}
        {failure ? (
          <div className="observable-event is-error" role="alert">
            <WarningCircle aria-hidden="true" size={18} />
            <div>
              <strong>Falha da demonstração</strong>
              <span>{failure}</span>
            </div>
          </div>
        ) : null}
      </div>
      <p className="activity-boundary">
        Apenas progresso factual e eventos permitidos. Sem raciocínio privado ou grader oculto.
      </p>
    </details>
  );
}
