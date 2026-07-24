import { motion, useReducedMotion } from "motion/react";

const labels = {
  idle: "Pronto para uma solicitação local",
  running: "Verificando referências autorizadas",
  success: "Resposta local capturada",
  failure: "Captura interrompida",
};

export function RegistrationProgress({ phase, cursor }) {
  const reduceMotion = useReducedMotion();
  const resolved = phase === "success";
  const failed = phase === "failure";

  return (
    <div
      className={`registration-progress is-${phase}`}
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      <span className="registration-label">{labels[phase] ?? labels.idle}</span>
      <div className="registration-track" aria-hidden="true">
        {[0, 1, 2, 3].map((mark) => {
          const active = phase === "running" && mark <= Math.max(cursor, 0);
          return (
            <motion.span
              className={`registration-mark${active ? " is-active" : ""}${
                resolved ? " is-resolved" : ""
              }${failed ? " is-failed" : ""}`}
              key={mark}
              initial={false}
              animate={
                reduceMotion
                  ? { opacity: resolved ? (mark === 3 ? 1 : 0.32) : 1 }
                  : {
                      opacity: resolved ? (mark === 3 ? 1 : 0.25) : 1,
                      scaleX: resolved ? (mark === 3 ? 1.6 : 0.6) : active ? 1.08 : 1,
                    }
              }
              transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            />
          );
        })}
      </div>
    </div>
  );
}
