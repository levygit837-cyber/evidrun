import { Check, Circle, Pulse } from "@phosphor-icons/react";

export function RunTrace({
  stages,
  currentStage,
  selectedStage,
  onSelect,
  label = "Traço da demonstração",
  compact = false,
}) {
  const currentIndex = stages.findIndex((stage) => stage.id === currentStage);

  return (
    <section className={`run-trace ${compact ? "run-trace--compact" : ""}`}>
      <div className="run-trace__heading">
        <p>{label}</p>
        <span>Estágio atual e seleção são estados independentes</span>
      </div>
      <ol aria-label={label}>
        {stages.map((stage, index) => {
          const status = index < currentIndex ? "completed" : index === currentIndex ? "current" : "future";
          const selected = stage.id === selectedStage;
          const Icon = status === "completed" ? Check : status === "current" ? Pulse : Circle;
          const stateLabel =
            status === "completed" ? "concluída" : status === "current" ? "atual" : "futura";

          return (
            <li key={stage.id} className={`run-trace__step run-trace__step--${status}`}>
              <button
                type="button"
                className={selected ? "is-selected" : ""}
                aria-current={status === "current" ? "step" : undefined}
                aria-pressed={selected}
                aria-label={`${stage.label}, ${stateLabel}${selected ? ", selecionada" : ""}`}
                onClick={() => onSelect?.(stage.id)}
              >
                <span className="run-trace__node" aria-hidden="true">
                  <Icon size={18} weight={status === "future" ? "regular" : "bold"} />
                </span>
                <span className="run-trace__label">{stage.label}</span>
              </button>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
