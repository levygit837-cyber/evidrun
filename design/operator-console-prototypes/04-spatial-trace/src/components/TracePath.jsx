import {
  Archive,
  BoundingBox,
  FileLock,
  Fingerprint,
  Notebook,
  Pulse,
  ShieldCheck,
} from "@phosphor-icons/react";
import { motion, useReducedMotion } from "motion/react";
import { workflowStages } from "../data/stubData.js";

const stageIcons = {
  intent: BoundingBox,
  revision: Notebook,
  runspec: FileLock,
  admission: ShieldCheck,
  run: Pulse,
  evaluation: Fingerprint,
  evidence: Archive,
};

export function TracePath({ activeStage, linkProps, onSelect, compact = false }) {
  const reduceMotion = useReducedMotion();
  const activeIndex = workflowStages.findIndex((stage) => stage.id === activeStage);

  return (
    <section className={compact ? "trace trace--compact" : "trace"} aria-label="Traço do workflow">
      <div className="trace__rail" aria-hidden="true">
        <motion.span
          className="trace__rail-progress"
          initial={reduceMotion ? false : { scaleX: 0 }}
          animate={{ scaleX: Math.max(0.04, activeIndex / (workflowStages.length - 1)) }}
          transition={{ duration: reduceMotion ? 0 : 0.22, ease: [0.16, 1, 0.3, 1] }}
        />
      </div>
      <ol className="trace__stages">
        {workflowStages.map((stage, index) => {
          const Icon = stageIcons[stage.id];
          const isActive = stage.id === activeStage;
          const isPast = index < activeIndex;
          const anchorProps = linkProps(stage.route);
          return (
            <li className="trace__stage" key={stage.id}>
              <a
                {...anchorProps}
                className="trace__stage-link"
                aria-current={isActive ? "step" : undefined}
                onClick={(event) => {
                  anchorProps.onClick(event);
                  onSelect?.(stage.id);
                }}
              >
                <motion.span
                  layout="position"
                  className={`trace__node ${isActive ? "is-active" : ""} ${isPast ? "is-past" : ""}`}
                  whileHover={reduceMotion ? undefined : { y: -2 }}
                  transition={{ duration: 0.18 }}
                >
                  <Icon aria-hidden="true" size={17} weight={isActive || isPast ? "fill" : "regular"} />
                </motion.span>
                <span className="trace__label">{stage.label}</span>
              </a>
              {isActive && !compact ? (
                <motion.div
                  className="trace__detail"
                  initial={reduceMotion ? false : { opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  {stage.short}
                </motion.div>
              ) : null}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
